#!/usr/bin/python3 -I
"""Read-only planner for the Android build toolchain (role android_build).

Looks up the latest stable releases at the vendors, applies the supply-chain cooldown and compares
them with what is installed. Prints one JSON plan on stdout; Ansible downloads, verifies and
installs. Writes nothing.

- JDK: Eclipse Temurin GA builds from the Adoptium API (SHA-256 from the API); the newest build whose
  binary is older than the cooldown.
- Command-line tools: the build published on developer.android.com/studio (the only place Google
  publishes a SHA-256 for it), cross-checked with the SHA-1 and revision in the repository XML;
  cooldown from the archive's Last-Modified header.
- SDK packages: newest stable-channel revision in the Google repository XML (system images in the
  sys-img XML of their tag); cooldown from the archive's Last-Modified header. sdkmanager installs
  them and checks the SHA-1 from the same XML (Google publishes no SHA-256 for these archives).
"""
from __future__ import annotations

import argparse
import calendar
import email.utils
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable

USER_AGENT = "ansible-android-build/1 (+python-urllib)"
TIMEOUT = 60
REPO_BASE = "https://dl.google.com/android/repository/"
ADOPTIUM_API = "https://api.adoptium.net/v3/assets/feature_releases/{feature}/ga"
STUDIO_PAGE = "https://developer.android.com/studio"

Revision = tuple[int, int, int]


class PlanError(RuntimeError):
    pass


# ---------- network (injectable for tests) ----------

def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PlanError(f"GET {url} failed: {exc}") from exc


def http_last_modified(url: str) -> float:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            value = resp.headers.get("Last-Modified")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PlanError(f"HEAD {url} failed: {exc}") from exc
    if not value:
        raise PlanError(f"HEAD {url}: no Last-Modified header, cannot apply the cooldown")
    return email.utils.parsedate_to_datetime(value).timestamp()


# ---------- versions ----------

def parse_jdk_version(text: str) -> tuple[tuple[int, ...], int]:
    """'21.0.13+9-LTS' or 'Temurin-21.0.12.1+1' -> ((21, 0, 13, 0), 9)."""
    m = re.search(r"(\d+(?:\.\d+)*)\+(\d+)", text)
    if not m:
        raise PlanError(f"unparsable JDK version {text!r}")
    nums = [int(x) for x in m.group(1).split(".")]
    nums += [0] * (4 - len(nums))
    return tuple(nums[:4]), int(m.group(2))


def installed_jdk_version(jdk_dir: Path) -> str | None:
    release = jdk_dir / "release"
    if not (jdk_dir / "bin" / "java").exists() or not release.exists():
        return None
    for line in release.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("JAVA_RUNTIME_VERSION="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def iso_ts(value: str) -> float:
    return float(calendar.timegm(time.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")))


def plan_jdk(releases: list[dict[str, Any]], installed: str | None, now: float, cooldown_s: float) -> dict[str, Any]:
    candidates = []
    deferred = []
    for rel in releases:
        bins = [b for b in rel.get("binaries", []) if b.get("image_type") == "jdk"]
        if not bins:
            continue
        b = bins[0]
        published = iso_ts(b["updated_at"])
        entry = {
            "version": rel["version_data"]["openjdk_version"],
            "release_name": rel["release_name"],
            "url": b["package"]["link"],
            "archive": b["package"]["name"],
            "sha256": b["package"]["checksum"],
            "published": b["updated_at"],
        }
        if now - published < cooldown_s:
            deferred.append(entry["release_name"])
        else:
            candidates.append(entry)
    if not candidates:
        raise PlanError("no Temurin build past the cooldown")
    target = max(candidates, key=lambda e: parse_jdk_version(e["version"]))
    update = installed is None or parse_jdk_version(target["version"]) > parse_jdk_version(installed)
    if not re.fullmatch(r"[0-9a-f]{64}", target["sha256"]):
        raise PlanError(f"Adoptium returned no SHA-256 for {target['release_name']}")
    return {**target, "installed": installed, "upgrade": update, "deferred": deferred}


def revision_of(elem: ET.Element) -> Revision:
    r = elem.find("revision")
    if r is None:
        return (0, 0, 0)
    return tuple(int(r.findtext(k) or 0) for k in ("major", "minor", "micro"))  # type: ignore[return-value]


def parse_revision_text(text: str) -> Revision:
    nums = [int(x) for x in re.findall(r"\d+", text)[:3]]
    nums += [0] * (3 - len(nums))
    return (nums[0], nums[1], nums[2])


def fmt_rev(rev: Revision) -> str:
    return ".".join(str(x) for x in rev)


def stable_channel(root: ET.Element) -> str:
    for ch in root.iter("channel"):
        if (ch.text or "").strip() == "stable":
            return ch.get("id", "channel-0")
    return "channel-0"


def linux_archive(pkg: ET.Element) -> dict[str, str] | None:
    for arch in pkg.iter("archive"):
        host_os = arch.findtext("host-os")
        host_arch = arch.findtext("host-arch")
        if host_os not in (None, "linux") or host_arch not in (None, "x64"):
            continue
        complete = arch.find("complete")
        if complete is None:
            continue
        sha1 = complete.find("checksum[@type='sha1']")
        return {"url": complete.findtext("url") or "", "sha1": (sha1.text if sha1 is not None else "") or ""}
    return None


def latest_stable(root: ET.Element, path: str) -> tuple[Revision, dict[str, str]] | None:
    channel = stable_channel(root)
    best: tuple[Revision, dict[str, str]] | None = None
    for pkg in root.findall("remotePackage"):
        if pkg.get("path") != path:
            continue
        ref = pkg.find("channelRef")
        if ref is not None and ref.get("ref") != channel:
            continue
        archive = linux_archive(pkg)
        if archive is None:
            continue
        rev = revision_of(pkg)
        if best is None or rev > best[0]:
            best = (rev, archive)
    return best


def installed_sdk_revision(sdk: Path, path: str) -> Revision | None:
    pkg_dir = sdk.joinpath(*path.split(";"))
    pkg_xml = pkg_dir / "package.xml"
    if pkg_xml.exists():
        local = ET.parse(pkg_xml).getroot().find("localPackage")
        if local is not None:
            return revision_of(local)
    props = pkg_dir / "source.properties"
    if props.exists():
        for line in props.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("Pkg.Revision="):
                return parse_revision_text(line.split("=", 1)[1])
    return None


def sysimg_xml_url(path: str, repo_base: str, schema: str) -> str:
    parts = path.split(";")
    if len(parts) != 4:
        raise PlanError(f"unexpected system image path {path!r}")
    return f"{repo_base}sys-img/{parts[2]}/sys-img2-{schema}.xml"


def plan_sdk(packages: list[str], sdk: Path, repo_base: str, schema: str, now: float, cooldown_s: float,
             get: Callable[[str], bytes], last_modified: Callable[[str], float]) -> dict[str, Any]:
    xml_cache: dict[str, ET.Element] = {}

    def root_for(url: str) -> ET.Element:
        if url not in xml_cache:
            xml_cache[url] = ET.fromstring(get(url))
        return xml_cache[url]

    install, current, deferred = [], [], []
    for path in packages:
        if path.startswith("system-images;"):
            xml_url = sysimg_xml_url(path, repo_base, schema)
        else:
            xml_url = f"{repo_base}repository2-{schema}.xml"
        found = latest_stable(root_for(xml_url), path)
        if found is None:
            raise PlanError(f"package {path} has no stable Linux x64 archive in {xml_url}")
        rev, archive = found
        have = installed_sdk_revision(sdk, path)
        if have is not None and have >= rev:
            current.append({"path": path, "revision": fmt_rev(have)})
            continue
        archive_url = xml_url.rsplit("/", 1)[0] + "/" + archive["url"]
        age = now - last_modified(archive_url)
        item = {"path": path, "revision": fmt_rev(rev), "installed": fmt_rev(have) if have else None}
        if age < cooldown_s:
            deferred.append({**item, "age_hours": round(age / 3600, 1)})
        else:
            install.append(item)
    return {"install": install, "current": current, "deferred": deferred}


def studio_cmdline_tools(html: str) -> tuple[str, str]:
    """Return (archive name, sha256) of the Linux command-line tools on developer.android.com/studio."""
    text = re.sub(r"<[^>]+>", " ", html)
    m = re.search(r"(commandlinetools-linux-\d+_latest\.zip)\s+[\d.]+\s*[MG]B\s+([0-9a-f]{64})", text)
    if not m:
        raise PlanError("developer.android.com/studio lists no Linux command-line tools with SHA-256")
    return m.group(1), m.group(2)


def plan_cmdline_tools(sdk: Path, repo_base: str, schema: str, now: float, cooldown_s: float,
                       get: Callable[[str], bytes], last_modified: Callable[[str], float]) -> dict[str, Any]:
    archive, sha256 = studio_cmdline_tools(get(STUDIO_PAGE).decode("utf-8", errors="replace"))
    repo = ET.fromstring(get(f"{repo_base}repository2-{schema}.xml"))
    match = None
    for pkg in repo.findall("remotePackage"):
        path = pkg.get("path") or ""
        if not re.fullmatch(r"cmdline-tools;\d+(\.\d+)*", path):
            continue
        arch = linux_archive(pkg)
        if arch and arch["url"] == archive:
            match = (revision_of(pkg), arch["sha1"])
            break
    if match is None:
        raise PlanError(f"{archive} from the studio page is not in the repository XML")
    rev, sha1 = match
    props = sdk / "cmdline-tools" / "latest" / "source.properties"
    have = None
    if (sdk / "cmdline-tools" / "latest" / "bin" / "sdkmanager").exists() and props.exists():
        have = installed_sdk_revision(sdk / "cmdline-tools", "latest")
    url = repo_base + archive
    update = have is None or rev > have
    age = now - last_modified(url) if update else None
    deferred = bool(update and age is not None and age < cooldown_s)
    return {
        "archive": archive, "url": url, "sha256": sha256, "sha1": sha1,
        "revision": fmt_rev(rev), "installed": fmt_rev(have) if have else None,
        "upgrade": update and not deferred, "deferred": deferred,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jdk-dir", required=True, type=Path)
    ap.add_argument("--jdk-feature", required=True, type=int)
    ap.add_argument("--sdk", required=True, type=Path)
    ap.add_argument("--packages", required=True, help="JSON list of sdkmanager package paths")
    ap.add_argument("--cooldown-hours", type=float, default=24.0)
    ap.add_argument("--repo-base", default=REPO_BASE)
    ap.add_argument("--repo-schema", default="3")
    args = ap.parse_args()

    packages = json.loads(args.packages)
    if not isinstance(packages, list) or not all(isinstance(p, str) and p for p in packages):
        raise PlanError("--packages must be a JSON list of non-empty strings")
    if not re.fullmatch(r"https://[^\s]+/", args.repo_base):
        raise PlanError("--repo-base must be an https URL ending in /")
    now = time.time()
    cooldown_s = args.cooldown_hours * 3600
    query = ("?architecture=x64&image_type=jdk&os=linux&jvm_impl=hotspot&vendor=eclipse"
             "&sort_order=DESC&page_size=10")
    releases = json.loads(http_get(ADOPTIUM_API.format(feature=args.jdk_feature) + query))
    plan = {
        "jdk": plan_jdk(releases, installed_jdk_version(args.jdk_dir), now, cooldown_s),
        "cmdline_tools": plan_cmdline_tools(args.sdk, args.repo_base, args.repo_schema, now, cooldown_s,
                                            http_get, http_last_modified),
        "sdk": plan_sdk(packages, args.sdk, args.repo_base, args.repo_schema, now, cooldown_s,
                        http_get, http_last_modified),
    }
    json.dump(plan, sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PlanError as exc:
        print(f"android_toolchain_plan: {exc}", file=sys.stderr)
        sys.exit(2)
