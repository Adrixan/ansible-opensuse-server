#!/usr/bin/env python3
"""Install or update Claude Desktop from Anthropic's signed apt repository.

Trust chain: InRelease is verified with gpgv against a pinned signing key and
the signer fingerprint is pinned; the Packages index and the .deb are then
verified by SHA256 against the signed metadata. Each version is unpacked into
its own directory under the install root and the stable install path is
switched over with an atomic symlink replace, so a running instance keeps its
files until it is restarted.

Prints CHANGED: <reason> when it modified the system, UP_TO_DATE otherwise.
"""

import argparse
import base64
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

VERSION_RE = re.compile(r"^[0-9]+(\.[0-9]+)*$")
FILENAME_RE = re.compile(r"^pool/main/c/claude-desktop/claude-desktop_[0-9.]+_amd64\.deb$")
DESKTOP_FILE = "com.anthropic.Claude.desktop"


def log(msg: str) -> None:
    print(msg, flush=True)


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out, length=1024 * 1024)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_stanzas(text: str) -> list[dict[str, str]]:
    stanzas, current, last_key = [], {}, None
    for line in text.splitlines():
        if not line.strip():
            if current:
                stanzas.append(current)
            current, last_key = {}, None
        elif line[0] in " \t" and last_key:
            current[last_key] += "\n" + line.strip()
        elif ":" in line:
            last_key, _, value = line.partition(":")
            current[last_key] = value.strip()
    if current:
        stanzas.append(current)
    return stanzas


def dearmor(armored: Path, dest: Path) -> None:
    """Convert an ASCII-armored public key into the binary form gpgv expects."""
    lines = armored.read_text().strip().splitlines()
    body = lines[lines.index("") + 1:lines.index("-----END PGP PUBLIC KEY BLOCK-----")]
    dest.write_bytes(base64.b64decode("".join(line for line in body if not line.startswith("="))))


def verify_inrelease(inrelease: Path, keyring: Path, fingerprint: str) -> str:
    """Return the signed Release content, or raise if the signature is not trusted."""
    result = subprocess.run(
        ["gpgv", "--status-fd", "2", "--keyring", str(keyring), "--output", "-", str(inrelease)],
        capture_output=True,
        check=False,
    )
    stderr = result.stderr.decode(errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"gpgv rejected InRelease: {stderr.strip()}")
    validsig = [line.split() for line in stderr.splitlines() if line.startswith("[GNUPG:] VALIDSIG ")]
    fingerprints = {fpr for fields in validsig for fpr in (fields[2], fields[-1])}
    if fingerprint.upper() not in fingerprints:
        raise RuntimeError(f"InRelease not signed by pinned key {fingerprint}")
    return result.stdout.decode()


def check_valid_until(release: dict[str, str]) -> None:
    valid_until = release.get("Valid-Until")
    if not valid_until:
        return
    expiry = datetime.strptime(valid_until, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
    if expiry < datetime.now(timezone.utc):
        raise RuntimeError(f"Repository metadata expired at {valid_until} (possible replay)")


def signed_hash(release: dict[str, str], path: str) -> str:
    for entry in release.get("SHA256", "").splitlines():
        parts = entry.split()
        if len(parts) == 3 and parts[2] == path:
            return parts[0]
    raise RuntimeError(f"No SHA256 for {path} in signed Release")


def select_package(packages: list[dict[str, str]], pin: str) -> dict[str, str]:
    candidates = [
        pkg for pkg in packages
        if pkg.get("Package") == "claude-desktop"
        and pkg.get("Architecture") == "amd64"
        and VERSION_RE.match(pkg.get("Version", ""))
        and FILENAME_RE.match(pkg.get("Filename", ""))
    ]
    if pin != "latest":
        candidates = [pkg for pkg in candidates if pkg["Version"] == pin]
    if not candidates:
        raise RuntimeError(f"No claude-desktop amd64 package matching version '{pin}'")
    return max(candidates, key=lambda pkg: version_key(pkg["Version"]))


def installed_version(install_dir: Path) -> str:
    try:
        return (install_dir / ".version").read_text().strip()
    except OSError:
        return ""


def replace_symlink(link: Path, target: str) -> None:
    tmp_link = link.with_name(f".{link.name}.new")
    if tmp_link.is_symlink() or tmp_link.exists():
        tmp_link.unlink()
    tmp_link.symlink_to(target)
    os.replace(tmp_link, link)


def migrate_legacy_dir(install_dir: Path, install_root: Path, check: bool) -> bool:
    """Convert a plain install directory into a versioned dir plus symlink."""
    if install_dir.is_symlink() or not install_dir.is_dir():
        return False
    version = installed_version(install_dir)
    name = f"claude-desktop-{version}" if VERSION_RE.match(version) else "claude-desktop-legacy"
    if check:
        log(f"CHANGED: would migrate {install_dir} to {install_root / name}")
        return True
    os.rename(install_dir, install_root / name)
    replace_symlink(install_dir, name)
    log(f"CHANGED: migrated {install_dir} to {install_root / name}")
    return True


def in_use(path: Path) -> bool:
    prefix = str(path) + "/"
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if os.readlink(proc / "exe").startswith(prefix):
                return True
        except OSError:
            continue
    return False


def prune(install_root: Path, install_dir: Path, keep: int) -> None:
    current = install_dir.resolve()
    versions = sorted(
        (d for d in install_root.glob("claude-desktop-*")
         if d.is_dir() and not d.is_symlink() and VERSION_RE.match(d.name.removeprefix("claude-desktop-"))),
        key=lambda d: version_key(d.name.removeprefix("claude-desktop-")),
        reverse=True,
    )
    for old in versions[max(keep, 1):]:
        if old.resolve() == current or in_use(old):
            continue
        shutil.rmtree(old)
        log(f"Pruned {old}")


def install(pkg: dict[str, str], base_url: str, install_root: Path, install_dir: Path) -> None:
    version = pkg["Version"]
    staging = Path(tempfile.mkdtemp(prefix=".claude-desktop-staging-", dir=install_root))
    try:
        deb = staging / "package.deb"
        download(f"{base_url}/{pkg['Filename']}", deb)
        if deb.stat().st_size != int(pkg["Size"]) or sha256_of(deb) != pkg["SHA256"]:
            raise RuntimeError(f"Checksum mismatch for {pkg['Filename']}")

        members = subprocess.run(["ar", "t", str(deb)], capture_output=True, text=True, check=True).stdout.split()
        data_member = next((m for m in members if re.fullmatch(r"data\.tar(\.(xz|zst|gz))?", m)), None)
        if not data_member:
            raise RuntimeError("No data.tar member in package")
        subprocess.run(["ar", "x", str(deb), data_member], cwd=staging, check=True)
        root = staging / "root"
        root.mkdir()
        subprocess.run(["tar", "--no-same-owner", "-xf", str(staging / data_member), "-C", str(root)], check=True)

        payload = root / "usr/lib/claude-desktop"
        if not (payload / "claude-desktop").is_file():
            raise RuntimeError("Package payload missing usr/lib/claude-desktop/claude-desktop")
        (payload / ".version").write_text(f"{version}\n")
        os.chmod(payload, 0o755)
        os.chmod(payload / "claude-desktop", 0o755)
        sandbox = payload / "chrome-sandbox"
        if sandbox.exists():
            os.chown(sandbox, 0, 0)
            os.chmod(sandbox, 0o4755)

        target = install_root / f"claude-desktop-{version}"
        if target.exists() and target.resolve() != install_dir.resolve():
            shutil.rmtree(target)
        if not target.exists():
            os.rename(payload, target)

        desktop_src = root / "usr/share/applications" / DESKTOP_FILE
        if desktop_src.is_file():
            desktop_tmp = Path("/usr/share/applications") / f".{DESKTOP_FILE}.new"
            shutil.copyfile(desktop_src, desktop_tmp)
            os.chmod(desktop_tmp, 0o644)
            os.replace(desktop_tmp, Path("/usr/share/applications") / DESKTOP_FILE)
        icons_src = root / "usr/share/icons/hicolor"
        if icons_src.is_dir():
            shutil.copytree(icons_src, "/usr/share/icons/hicolor", dirs_exist_ok=True)

        replace_symlink(install_dir, target.name)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default="https://downloads.claude.ai/claude-desktop/apt/stable")
    parser.add_argument("--key", default="/usr/share/keyrings/claude-desktop.asc", type=Path,
                        help="ASCII-armored repository signing key")
    parser.add_argument("--fingerprint", required=True)
    parser.add_argument("--install-root", default="/opt", type=Path)
    parser.add_argument("--install-dir", default="/opt/claude-desktop", type=Path)
    parser.add_argument("--version", default="latest", help="exact version to install, or 'latest'")
    parser.add_argument("--keep", default=2, type=int, help="number of versions to keep on disk")
    parser.add_argument("--check", action="store_true", help="report what would change without changing anything")
    args = parser.parse_args()

    if args.version != "latest" and not VERSION_RE.match(args.version):
        parser.error(f"invalid version '{args.version}'")

    changed = migrate_legacy_dir(args.install_dir, args.install_root, args.check)

    with tempfile.TemporaryDirectory(prefix="claude-desktop-meta-") as tmp:
        tmpdir = Path(tmp)
        dearmor(args.key, tmpdir / "keyring.gpg")
        download(f"{args.repo}/dists/stable/InRelease", tmpdir / "InRelease")
        release = parse_stanzas(verify_inrelease(tmpdir / "InRelease", tmpdir / "keyring.gpg", args.fingerprint))[0]
        check_valid_until(release)
        index_path = "main/binary-amd64/Packages"
        download(f"{args.repo}/dists/stable/{index_path}", tmpdir / "Packages")
        if sha256_of(tmpdir / "Packages") != signed_hash(release, index_path):
            raise RuntimeError("Packages index does not match signed Release")
        pkg = select_package(parse_stanzas((tmpdir / "Packages").read_text()), args.version)

    current = installed_version(args.install_dir)
    if current == pkg["Version"]:
        if not args.check:
            prune(args.install_root, args.install_dir, args.keep)
        if not changed:
            log(f"UP_TO_DATE {current}")
        return 0

    if args.check:
        log(f"CHANGED: would update Claude Desktop {current or 'none'} -> {pkg['Version']}")
        return 0

    install(pkg, args.repo, args.install_root, args.install_dir)
    log(f"CHANGED: updated Claude Desktop {current or 'none'} -> {pkg['Version']}")
    prune(args.install_root, args.install_dir, args.keep)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - surface any failure as a non-zero exit for systemd/Ansible
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
