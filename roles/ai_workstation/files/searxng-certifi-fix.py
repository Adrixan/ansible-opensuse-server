"""Replace the bundled certifi with a hash-verified release (build step of the local SearXNG image).

The upstream image has no pip; certifi is pure Python, so its wheel is unpacked over the old copy.
Usage: python searxng-certifi-fix.py <wheel-url> <sha256>
"""

import glob
import hashlib
import io
import shutil
import sys
import urllib.request
import zipfile


def main() -> None:
    url, expected = sys.argv[1], sys.argv[2]
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        sys.exit(f"certifi wheel checksum mismatch: {actual} != {expected}")
    sites = glob.glob("/usr/local/searxng/.venv/lib/python3.*/site-packages")
    if len(sites) != 1:
        sys.exit(f"expected one site-packages directory, found {sites}")
    for old in glob.glob(f"{sites[0]}/certifi*"):
        shutil.rmtree(old)
    zipfile.ZipFile(io.BytesIO(data)).extractall(sites[0])


main()
