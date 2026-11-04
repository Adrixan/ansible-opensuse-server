#!/usr/bin/python3
"""Keep ~/code the same on every workstation, with the git remotes as the only transport.

1. register: every local repository with an `origin` goes into a shared list (a TSV in a Syncthing
   folder: name, origin URL), so the other machines learn about it;
2. clone: repositories on the list that are missing here are cloned (with submodules);
3. update: every repository is fetched; branches that track an upstream are fast-forwarded when that
   loses nothing (the checked-out branch only with a clean working tree);
4. report: repositories with uncommitted changes, unpushed commits or commits on no remote are listed,
   because only pushed work reaches the other machine.

Never merges, rebases, resets or deletes. A per-machine exclude file names repositories that stay off
this machine (one name per line).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def git(repo: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=check,
                          env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})


def read_list(path: Path) -> dict[str, str]:
    repos: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                name, _, url = line.partition("\t")
                if name and url:
                    repos[name] = url
    return repos


def write_list(path: Path, repos: dict[str, str]) -> None:
    text = "# Repositories in ~/code (name<TAB>origin), maintained by code-sync on every workstation\n"
    text += "".join(f"{n}\t{u}\n" for n, u in sorted(repos.items(), key=lambda kv: kv[0].lower()))
    if path.exists() and path.read_text() == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".syncthing.{path.name}.code-sync.tmp")  # Syncthing ignores this name
    tmp.write_text(text)
    os.replace(tmp, path)


def local_repos(code: Path) -> list[Path]:
    return sorted(p.parent for p in code.glob("*/.git"))


def update(repo: Path) -> list[str]:
    notes: list[str] = []
    if git(repo, "fetch", "--all", "--prune", "--quiet").returncode != 0:
        return ["fetch failed"]
    dirty = bool(git(repo, "status", "--porcelain").stdout.strip())
    current = git(repo, "symbolic-ref", "-q", "--short", "HEAD").stdout.strip()
    refs = git(repo, "for-each-ref", "--format=%(refname:short)\t%(upstream:short)", "refs/heads").stdout
    for line in refs.splitlines():
        branch, _, upstream = line.partition("\t")
        if not upstream:
            if git(repo, "rev-list", "-n1", branch, "--not", "--remotes").stdout.strip():
                notes.append(f"{branch}: commits on no remote")
            continue
        if git(repo, "rev-parse", "-q", "--verify", upstream).returncode != 0:
            notes.append(f"{branch}: upstream {upstream} gone")
            continue
        ahead = int(git(repo, "rev-list", "--count", f"{upstream}..{branch}").stdout or 0)
        behind = int(git(repo, "rev-list", "--count", f"{branch}..{upstream}").stdout or 0)
        if ahead:
            notes.append(f"{branch}: {ahead} unpushed")
        if behind and not ahead:
            if branch == current:
                if dirty:
                    notes.append(f"{branch}: {behind} behind, not updated (uncommitted changes)")
                elif git(repo, "merge", "--ff-only", "--quiet", upstream).returncode != 0:
                    notes.append(f"{branch}: fast-forward failed")
            else:
                sha = git(repo, "rev-parse", upstream).stdout.strip()
                git(repo, "update-ref", f"refs/heads/{branch}", sha)
    if dirty:
        notes.append("uncommitted changes")
    if (repo / ".gitmodules").exists() and not dirty:
        git(repo, "submodule", "update", "--init", "--recursive", "--quiet")
    return notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--code", type=Path, default=Path.home() / "code")
    ap.add_argument("--list", type=Path, default=Path.home() / "sync/ai/code-repos.tsv")
    ap.add_argument("--exclude", type=Path, default=Path.home() / ".config/code-sync/exclude")
    ap.add_argument("--no-clone", action="store_true", help="only register, update and report")
    args = ap.parse_args()
    exclude = set(args.exclude.read_text().split()) if args.exclude.exists() else set()

    repos = read_list(args.list)
    for repo in local_repos(args.code):
        url = git(repo, "remote", "get-url", "origin").stdout.strip()
        if url and repo.name not in exclude and repos.get(repo.name) != url:
            repos[repo.name] = url
    write_list(args.list, repos)

    problems = 0
    if not args.no_clone:
        for name, url in repos.items():
            target = args.code / name
            if name in exclude or target.exists():
                continue
            r = subprocess.run(["git", "clone", "--quiet", "--recurse-submodules", url, str(target)],
                               capture_output=True, text=True, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
            print(f"cloned {name}" if r.returncode == 0 else f"{name}: clone failed: {r.stderr.strip()[:200]}")
            problems += r.returncode != 0
    for repo in local_repos(args.code):
        if repo.name in exclude:
            continue
        notes = update(repo)
        if notes:
            print(f"{repo.name}: " + "; ".join(notes))
            problems += any("failed" in n for n in notes)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
