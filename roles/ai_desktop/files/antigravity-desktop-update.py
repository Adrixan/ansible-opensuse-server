#!/usr/bin/env python3
"""Install or update Google Antigravity Desktop from the official release repository.

Queries the official release feed for the target version and build execution ID,
fetches signed object metadata (size and CRC32C) from the Google Cloud Storage
JSON API over TLS, verifies the downloaded archive against both size and CRC32C,
unpacks each version into its own directory under the install root, and switches
the stable install path with an atomic symlink replacement so a running instance
keeps its files until restarted.

Prints CHANGED: <reason> when it modified the system, UP_TO_DATE otherwise.
"""

import argparse
import base64
import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

VERSION_RE = re.compile(r"^[0-9]+(\.[0-9]+)*$")
EXECUTION_ID_RE = re.compile(r"^[0-9]+$")


def log(msg: str) -> None:
    print(msg, flush=True)


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def fetch_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": "antigravity-desktop-update/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "antigravity-desktop-update/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out, length=1024 * 1024)


def _make_crc32c_table() -> list[int]:
    poly = 0x82F63B78
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            crc = (crc >> 1) ^ poly if (crc & 1) else (crc >> 1)
        table.append(crc)
    return table


def crc32c_b64_of(path: Path) -> str:
    """Compute the base64-encoded big-endian CRC32C of a file (matching GCS object metadata)."""
    try:
        lib = ctypes.CDLL("libcrc32c.so.1")
        lib.crc32c_extend.argtypes = [ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t]
        lib.crc32c_extend.restype = ctypes.c_uint32
        crc = 0
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                crc = lib.crc32c_extend(crc, chunk, len(chunk))
    except OSError:
        table = _make_crc32c_table()
        crc = 0xFFFFFFFF
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                for b in chunk:
                    crc = table[(crc ^ b) & 0xFF] ^ (crc >> 8)
        crc ^= 0xFFFFFFFF
    return base64.b64encode(crc.to_bytes(4, "big")).decode("ascii")


def select_release(payload: object, pin: str) -> dict[str, str]:
    entries = payload.get("versions") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise RuntimeError("Unexpected releases payload structure")
    candidates = [
        item for item in entries
        if isinstance(item, dict)
        and VERSION_RE.match(str(item.get("version", "")))
        and EXECUTION_ID_RE.match(str(item.get("execution_id", "")))
    ]
    if pin != "latest":
        candidates = [item for item in candidates if item["version"] == pin]
    if not candidates:
        raise RuntimeError(f"No Antigravity Desktop release matching version '{pin}'")
    return max(candidates, key=lambda item: version_key(item["version"]))


def installed_version(install_dir: Path) -> str:
    try:
        raw = (install_dir / ".version").read_text().strip()
        return raw.split("-", 1)[0]
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
    name = f"antigravity-{version}" if VERSION_RE.match(version) else "antigravity-legacy"
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


def prune(install_root: Path, install_dir: Path, keep: int, check: bool) -> bool:
    """Remove superseded versions; a version a process is running from is kept until it exits."""
    current = install_dir.resolve()
    versions = sorted(
        (d for d in install_root.glob("antigravity-*")
         if d.is_dir() and not d.is_symlink() and VERSION_RE.match(d.name.removeprefix("antigravity-"))),
        key=lambda d: version_key(d.name.removeprefix("antigravity-")),
        reverse=True,
    )
    changed = False
    for old in versions[max(keep, 1):]:
        if old.resolve() == current:
            continue
        if in_use(old):
            log(f"KEEP {old} (in use, restart Antigravity Desktop to release it)")
            continue
        if check:
            log(f"CHANGED: would prune {old}")
        else:
            shutil.rmtree(old)
            log(f"CHANGED: pruned {old}")
        changed = True
    return changed


def install(
    release: dict[str, str],
    bucket_url: str,
    metadata_url: str,
    install_root: Path,
    install_dir: Path,
) -> None:
    version = release["version"]
    execution_id = release["execution_id"]
    rel_object = f"{version}-{execution_id}/linux-x64/Antigravity.tar.gz"
    gcs_object = f"antigravity-hub/{rel_object}"

    meta = fetch_json(f"{metadata_url}/{urllib.parse.quote(gcs_object, safe='')}")
    if not isinstance(meta, dict) or "size" not in meta or "crc32c" not in meta:
        raise RuntimeError(f"Missing size or crc32c in GCS metadata for {gcs_object}")
    expected_size = int(meta["size"])
    expected_crc32c = str(meta["crc32c"])

    staging = Path(tempfile.mkdtemp(prefix=".antigravity-staging-", dir=install_root))
    try:
        archive = staging / "Antigravity.tar.gz"
        download(f"{bucket_url}/{rel_object}", archive)
        if archive.stat().st_size != expected_size or crc32c_b64_of(archive) != expected_crc32c:
            raise RuntimeError(f"Checksum or size mismatch for {gcs_object}")

        payload = staging / "payload"
        payload.mkdir()
        subprocess.run(
            ["tar", "--no-same-owner", "--strip-components=1", "-xzf", str(archive), "-C", str(payload)],
            check=True,
        )

        binary = payload / "antigravity"
        if not binary.is_file():
            raise RuntimeError("Archive payload missing antigravity binary")
        (payload / ".version").write_text(f"{version}\n")
        os.chmod(payload, 0o755)
        os.chmod(binary, 0o755)
        sandbox = payload / "chrome-sandbox"
        if sandbox.exists():
            os.chown(sandbox, 0, 0)
            os.chmod(sandbox, 0o4755)

        target = install_root / f"antigravity-{version}"
        if target.exists() and (not install_dir.exists() or target.resolve() != install_dir.resolve()):
            shutil.rmtree(target)
        if not target.exists():
            os.rename(payload, target)

        replace_symlink(install_dir, target.name)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--releases-url",
        default="https://antigravity-hub-auto-updater-974169037036.us-central1.run.app/releases",
    )
    parser.add_argument(
        "--bucket-url",
        default="https://storage.googleapis.com/antigravity-public/antigravity-hub",
    )
    parser.add_argument(
        "--metadata-url",
        default="https://storage.googleapis.com/storage/v1/b/antigravity-public/o",
    )
    parser.add_argument("--install-root", default="/opt", type=Path)
    parser.add_argument("--install-dir", default="/opt/antigravity", type=Path)
    parser.add_argument("--version", default="latest", help="exact version to install, or 'latest'")
    parser.add_argument("--keep", default=1, type=int, help="number of versions to keep on disk")
    parser.add_argument("--check", action="store_true", help="report what would change without changing anything")
    args = parser.parse_args()

    if args.version != "latest" and not VERSION_RE.match(args.version):
        parser.error(f"invalid version '{args.version}'")

    changed = migrate_legacy_dir(args.install_dir, args.install_root, args.check)
    release = select_release(fetch_json(args.releases_url), args.version)

    current = installed_version(args.install_dir)
    if current == release["version"]:
        pruned = prune(args.install_root, args.install_dir, args.keep, args.check)
        if not (changed or pruned):
            log(f"UP_TO_DATE {current}")
        return 0

    if args.check:
        log(f"CHANGED: would update Antigravity Desktop {current or 'none'} -> {release['version']}")
        return 0

    install(release, args.bucket_url, args.metadata_url, args.install_root, args.install_dir)
    log(f"CHANGED: updated Antigravity Desktop {current or 'none'} -> {release['version']}")
    prune(args.install_root, args.install_dir, args.keep, check=False)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - surface any failure as a non-zero exit for systemd/Ansible
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
