#!/usr/bin/env python3
"""Remove legacy gateway overrides from ~/.claude/settings.json and keep everything else.

Usage: claude_settings_sanitize.py <settings.json> <legacy env key> [...]

Only the named keys inside "env" go (the old Bailian gateway variables); other env entries, such as
CLAUDE_CODE_EXPERIMENTAL_CODE_MODE or DISABLE_AUTOUPDATER from the yadm-tracked file, stay. An "env"
block is dropped only when this purge emptied it. The file is rewritten atomically, with literal
non-ASCII characters (ensure_ascii=False), the same indent and the original mode, and only on change.
Prints CHANGED or ALREADY_SET; exits 1 on unreadable JSON so the playbook stops instead of guessing.
"""
import json
import os
import sys
import tempfile

LEGACY_TOP_LEVEL = ("modelOverrides", "autoCompactWindow")
LEGACY_MODELS = {"qwen3.7-plus", "qwen3.8-max", "qwen3.8-flash", "deepseek-v4-pro", "glm-5.2"}


def sanitize(data: dict, legacy_env: set[str]) -> list[str]:
    removed: list[str] = []
    env = data.get("env")
    if isinstance(env, dict):
        for key in sorted(legacy_env & env.keys()):
            del env[key]
            removed.append(f"env.{key}")
        if removed and not env:
            del data["env"]
    for key in LEGACY_TOP_LEVEL:
        if key in data:
            del data[key]
            removed.append(key)
    if data.get("model") in LEGACY_MODELS:
        removed.append(f"model={data.pop('model')}")
    return removed


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    path, legacy_env = sys.argv[1], set(sys.argv[2:])
    if not os.path.exists(path):
        print("ALREADY_SET")
        return 0
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"ERROR: cannot read {path}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print(f"ERROR: {path} is not a JSON object", file=sys.stderr)
        return 1
    removed = sanitize(data, legacy_env)
    if not removed:
        print("ALREADY_SET")
        return 0
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".settings.json.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.chmod(tmp, os.stat(path).st_mode & 0o777)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
    print("CHANGED: removed " + ", ".join(removed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
