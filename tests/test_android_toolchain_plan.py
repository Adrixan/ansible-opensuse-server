"""Tests for roles/android_build/files/android_toolchain_plan.py (run: python3 -I tests/test_android_toolchain_plan.py)."""
import importlib.util
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "roles/android_build/files/android_toolchain_plan.py"
spec = importlib.util.spec_from_file_location("atp", SRC)
atp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atp)

fails = 0


def check(name, cond):
    global fails
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails += 1


def raises(fn):
    try:
        fn()
    except atp.PlanError:
        return True
    return False


NOW = 1_800_000_000.0
DAY = 86400.0
BASE = "https://dl.google.com/android/repository/"


def pkg(path, rev, channel, url, host_os="linux", host_arch=None):
    major, minor, micro = (rev + (0, 0))[:3]
    arch = f"<host-arch>{host_arch}</host-arch>" if host_arch else ""
    hos = f"<host-os>{host_os}</host-os>" if host_os else ""
    return (f'<remotePackage path="{path}"><revision><major>{major}</major><minor>{minor}</minor>'
            f'<micro>{micro}</micro></revision><channelRef ref="{channel}"/><archives><archive><complete>'
            f'<size>1</size><checksum type="sha1">{"a" * 40}</checksum><url>{url}</url></complete>{hos}{arch}'
            f'</archive></archives></remotePackage>')


REPO = ("<repo><channel id='channel-0'>stable</channel><channel id='channel-2'>dev</channel>"
        + pkg("platform-tools", (37, 0, 1), "channel-0", "pt-37.0.1-linux.zip")
        + pkg("platform-tools", (37, 0, 2), "channel-2", "pt-37.0.2-linux.zip")
        + pkg("platform-tools", (38, 0, 0), "channel-0", "pt-38-darwin.zip", host_os="macosx")
        + pkg("emulator", (37, 2, 13), "channel-0", "emu-arm.zip", host_arch="aarch64")
        + pkg("emulator", (37, 2, 12), "channel-0", "emu-x64.zip", host_arch="x64")
        + pkg("cmdline-tools;22.0", (22, 0), "channel-0", "commandlinetools-linux-15859902_latest.zip")
        + pkg("cmdline-tools;23.0", (23, 0), "channel-0", "commandlinetools-linux-16111833_latest.zip")
        + "</repo>")
SYSIMG = ("<repo><channel id='channel-0'>stable</channel>"
          + pkg("system-images;android-36;google_apis;x86_64", (7,), "channel-0", "x86_64-36_r07.zip", host_os=None)
          + "</repo>")
STUDIO = ("<tr><td><button>commandlinetools-linux-15859902_latest.zip</button></td><td>181.8 MB</td>"
          "<td>" + "4e" * 32 + "</td></tr>")

FILES = {
    BASE + "repository2-3.xml": REPO.encode(),
    BASE + "sys-img/google_apis/sys-img2-3.xml": SYSIMG.encode(),
    atp.STUDIO_PAGE: STUDIO.encode(),
}


def get(url):
    return FILES[url]


def lm_old(_url):
    return NOW - 30 * DAY


def lm_young(_url):
    return NOW - 3600.0


# --- versions
check("jdk version parse", atp.parse_jdk_version("21.0.13+9-LTS") == ((21, 0, 13, 0), 9))
check("jdk patch release sorts above base", atp.parse_jdk_version("21.0.12.1+1") > atp.parse_jdk_version("21.0.12+8"))
check("jdk version from IMPLEMENTOR_VERSION", atp.parse_jdk_version("Temurin-21.0.13+9") == ((21, 0, 13, 0), 9))
check("unparsable jdk version raises", raises(lambda: atp.parse_jdk_version("garbage")))
check("revision text", atp.parse_revision_text("22.0") == (22, 0, 0))
check("iso timestamp is UTC", atp.iso_ts("1970-01-02T00:00:00Z") == 86400.0)


# --- JDK plan
def rel(version, name, updated, sha="d7" * 32):
    return {"release_name": name, "version_data": {"openjdk_version": version},
            "binaries": [{"image_type": "jdk", "updated_at": updated,
                          "package": {"link": f"https://example.invalid/{name}.tar.gz", "name": f"{name}.tar.gz",
                                      "checksum": sha}}]}


def ts(offset):
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW + offset))


releases = [rel("21.0.14+7-LTS", "jdk-21.0.14+7", ts(-3600)), rel("21.0.13+9-LTS", "jdk-21.0.13+9", ts(-20 * DAY))]
p = atp.plan_jdk(releases, "21.0.13+9-LTS", NOW, DAY)
check("young JDK deferred, installed kept", not p["upgrade"] and p["deferred"] == ["jdk-21.0.14+7"])
p = atp.plan_jdk(releases, None, NOW, DAY)
check("fresh host gets newest JDK past cooldown", p["upgrade"] and p["release_name"] == "jdk-21.0.13+9")
p = atp.plan_jdk(releases, "21.0.12+8-LTS", NOW, 0)
check("older install updates to newest", p["upgrade"] and p["release_name"] == "jdk-21.0.14+7")
p = atp.plan_jdk(releases[1:], "21.0.14+7-LTS", NOW, DAY)
check("never downgrades", not p["upgrade"])
check("missing sha256 raises", raises(lambda: atp.plan_jdk([rel("21.0.13+9-LTS", "x", ts(-20 * DAY), sha="")], None, NOW, DAY)))
check("nothing past cooldown raises", raises(lambda: atp.plan_jdk(releases[:1], None, NOW, DAY)))

with tempfile.TemporaryDirectory() as d:
    jdk = Path(d) / "jdk-21"
    (jdk / "bin").mkdir(parents=True)
    check("no java -> not installed", atp.installed_jdk_version(jdk) is None)
    (jdk / "bin" / "java").write_text("")
    (jdk / "release").write_text('IMPLEMENTOR="Eclipse Adoptium"\nJAVA_RUNTIME_VERSION="21.0.13+9-LTS"\n')
    check("installed jdk from release file", atp.installed_jdk_version(jdk) == "21.0.13+9-LTS")

# --- SDK packages
root = atp.ET.fromstring(REPO)
best = atp.latest_stable(root, "platform-tools")
check("stable channel only, linux only", best[0] == (37, 0, 1) and best[1]["url"] == "pt-37.0.1-linux.zip")
best = atp.latest_stable(root, "emulator")
check("x64 archive chosen over aarch64", best[0] == (37, 2, 12) and best[1]["url"] == "emu-x64.zip")
check("unknown package -> None", atp.latest_stable(root, "nope") is None)
check("bad system image path raises", raises(lambda: atp.sysimg_xml_url("system-images;android-36", BASE, "3")))

pkgs = ["platform-tools", "emulator", "system-images;android-36;google_apis;x86_64"]
with tempfile.TemporaryDirectory() as d:
    sdk = Path(d)
    p = atp.plan_sdk(pkgs, sdk, BASE, "3", NOW, DAY, get, lm_old)
    check("empty sdk installs all", [i["path"] for i in p["install"]] == pkgs and not p["current"])
    p = atp.plan_sdk(pkgs, sdk, BASE, "3", NOW, DAY, get, lm_young)
    check("young archives deferred", not p["install"] and len(p["deferred"]) == 3)
    (sdk / "platform-tools").mkdir()
    (sdk / "platform-tools" / "package.xml").write_text(
        "<repo><localPackage path='platform-tools'><revision><major>37</major><minor>0</minor>"
        "<micro>1</micro></revision></localPackage></repo>")
    img = sdk / "system-images" / "android-36" / "google_apis" / "x86_64"
    img.mkdir(parents=True)
    (img / "source.properties").write_text("Pkg.Revision=6\n")
    p = atp.plan_sdk(pkgs, sdk, BASE, "3", NOW, DAY, get, lm_old)
    check("current package skipped", [c["path"] for c in p["current"]] == ["platform-tools"])
    check("outdated image (source.properties) updated",
          {"path": pkgs[2], "revision": "7.0.0", "installed": "6.0.0"} in p["install"])
    check("missing package raises", raises(lambda: atp.plan_sdk(["nope"], sdk, BASE, "3", NOW, DAY, get, lm_old)))

    # --- command-line tools
    name, sha = atp.studio_cmdline_tools(STUDIO)
    check("studio page parsed", name == "commandlinetools-linux-15859902_latest.zip" and sha == "4e" * 32)
    check("studio page without hash raises", raises(lambda: atp.studio_cmdline_tools("<p>nothing</p>")))
    p = atp.plan_cmdline_tools(sdk, BASE, "3", NOW, DAY, get, lm_young)
    check("fresh host, young zip deferred", p["deferred"] and not p["upgrade"])
    p = atp.plan_cmdline_tools(sdk, BASE, "3", NOW, DAY, get, lm_old)
    check("follows the studio build, not the newest XML revision", p["upgrade"] and p["revision"] == "22.0.0"
          and p["sha1"] == "a" * 40)
    latest = sdk / "cmdline-tools" / "latest"
    (latest / "bin").mkdir(parents=True)
    (latest / "bin" / "sdkmanager").write_text("")
    (latest / "source.properties").write_text("Pkg.Revision=22.0\nPkg.Path=cmdline-tools;22.0\n")
    p = atp.plan_cmdline_tools(sdk, BASE, "3", NOW, DAY, get, lm_young)
    check("installed studio build -> no update", not p["upgrade"] and not p["deferred"] and p["installed"] == "22.0.0")

print(f"{fails} failure(s)")
sys.exit(1 if fails else 0)
