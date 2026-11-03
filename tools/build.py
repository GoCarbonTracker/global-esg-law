#!/usr/bin/env python3
"""Build dated instrument commits from admitted source rows and JSON records."""
import json
import os
import subprocess
import sys
import tempfile
from datetime import date, datetime, time, timezone
from pathlib import Path

from check_corpus import check

ROOT = Path(__file__).resolve().parents[1]


class BranchRequired(ValueError):
    """Raised when records/ is tracked by git and no --branch was given (exit 2 on the command line)."""


def git(repo, *args, env=None):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env).stdout.strip()


def records_tracked(repo):
    """True when any file under records/ is tracked by git, so a build must name its branch."""
    return bool(git(repo, "ls-files", "--", "records"))


def build(repo=ROOT, branch=None):
    """Commit each record in in-force order. With branch, build it from scratch as an orphan history
    (cumulative trees, file content in each commit) without touching the working tree or index.
    Without branch, commits land on the checked-out branch, which is allowed only while nothing
    under records/ is tracked (an empty repository, as in the tests)."""
    repo = Path(repo).resolve()
    if not branch and records_tracked(repo):
        raise BranchRequired("records/ is tracked by git: --branch is required (python3 tools/build.py --branch history)")
    check(repo)
    if branch and git(repo, "symbolic-ref", "-q", "HEAD") == f"refs/heads/{branch}":
        raise ValueError(f"{branch} is the checked-out branch; refusing to replace it")
    rows = {r["id"]: r for r in json.loads((repo / "sources.json").read_text())}
    records = []
    for path in sorted((repo / "records").rglob("*.json")):
        record = json.loads(path.read_text())
        row_id = record["source_id"]
        row = rows[row_id]
        # A record whose commencement is unknown has in_force null: its file name starts with the date it is filed under.
        effective = date.fromisoformat(record["in_force"] or path.name[:10])
        iso2, instrument_id = path.relative_to(repo / "records").parts[:2]
        scope = json.loads((repo / "register" / iso2 / "scope.json").read_text())
        entry = next(e for e in scope if e["id"] == instrument_id)
        row = {**row, "trailer_instrument": entry["title"], "trailer_source_url": entry["official_url"],
               "iso2": iso2, "instrument_id": instrument_id}
        records.append((effective, row_id, path, record, row))
    # Same date and instrument: official-language records first (a translation never replaces one in a
    # lookup), then by language code, then as before.
    records.sort(key=lambda item: (item[0], item[4]["trailer_instrument"], item[3]["kind"] == "translation",
                                   item[3]["language"], item[1], item[2].as_posix()))
    tmp = tempfile.TemporaryDirectory()
    index = Path(tmp.name) / "index"
    parent = None
    for effective, row_id, path, record, row in records:
        env = os.environ.copy()
        timestamp = datetime.combine(max(effective, date(1970, 1, 1)), time(12), timezone.utc).strftime("%Y-%m-%dT%H:%M:%S +0000")
        env.update(GIT_AUTHOR_DATE=timestamp, GIT_COMMITTER_DATE=timestamp)
        repeal = record.get("repealed") is True  # a repeal record: empty text, Kind trailer `repeal`
        verb, kind = ("repealed", "repeal") if repeal else ("effective", record["kind"])
        message = (record.get("message") or f"{row['trailer_instrument']} {verb} {effective}") + "\n\n"
        message += (f"Instrument: {row['trailer_instrument']}\nSource-url: {row['trailer_source_url']}\n"
                    f"In-force: {effective}\nKind: {kind}\nLicence: {row['trailer_licence']}\n"
                    f"Jurisdiction: {row['iso2']}\nInstrument-id: {row['instrument_id']}\nLanguage: {record['language']}")
        ident = ["-c", "user.name=Global ESG Law Builder", "-c", "user.email=builder@global-esg-law.invalid"]
        rel = str(path.relative_to(repo))
        if branch:
            env["GIT_INDEX_FILE"] = str(index)
            blob = git(repo, "hash-object", "-w", "--", rel)
            git(repo, "update-index", "--add", "--cacheinfo", f"100644,{blob},{rel}", env=env)
            tree = git(repo, "write-tree", env=env)
            parent = git(repo, *ident, "commit-tree", tree, *(["-p", parent] if parent else []), "-m", message, env=env)
        else:
            git(repo, "add", "--", rel, env=env)
            git(repo, *ident, "commit", "--allow-empty", "-m", message, env=env)
    if branch:
        tmp.cleanup()
        if parent:
            git(repo, "update-ref", f"refs/heads/{branch}", parent)
    return [(str(d), r["trailer_instrument"]) for d, _, _, _, r in records]


def main(argv):
    """`python3 tools/build.py --branch <name> [--repo PATH]`. Exit 2 when --branch is missing on a populated repo."""
    def flag(name):
        value = argv[argv.index(name) + 1:argv.index(name) + 2] if name in argv else []
        return value[0] if value and not value[0].startswith("--") else None

    branch, repo = flag("--branch"), flag("--repo") or ROOT
    try:
        build(repo, branch=branch)
    except BranchRequired as exc:
        print(exc, file=sys.stderr)
        return 2
    except (KeyError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
