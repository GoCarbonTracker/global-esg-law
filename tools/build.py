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


def git(repo, *args, env=None):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env).stdout.strip()


def build(repo=ROOT, branch=None):
    """Commit each record in in-force order. With branch, build it from scratch as an orphan history
    (cumulative trees, file content in each commit) without touching the working tree or index."""
    repo = Path(repo).resolve()
    check(repo)
    if branch and git(repo, "symbolic-ref", "-q", "HEAD") == f"refs/heads/{branch}":
        raise ValueError(f"{branch} is the checked-out branch; refusing to replace it")
    rows = {r["id"]: r for r in json.loads((repo / "sources.json").read_text())}
    records = []
    for path in sorted((repo / "records").rglob("*.json")):
        record = json.loads(path.read_text())
        row_id = record["source_id"]
        row = rows[row_id]
        effective = date.fromisoformat(record["in_force"])
        iso2, instrument_id = path.relative_to(repo / "records").parts[:2]
        scope = json.loads((repo / "register" / iso2 / "scope.json").read_text())
        entry = next(e for e in scope if e["id"] == instrument_id)
        row = {**row, "trailer_instrument": entry["title"], "trailer_source_url": entry["official_url"],
               "iso2": iso2, "instrument_id": instrument_id}
        records.append((effective, row_id, path, record, row))
    records.sort(key=lambda item: (item[0], item[4]["trailer_instrument"], item[1], item[2].as_posix()))
    tmp = tempfile.TemporaryDirectory()
    index = Path(tmp.name) / "index"
    parent = None
    for effective, row_id, path, record, row in records:
        env = os.environ.copy()
        timestamp = datetime.combine(max(effective, date(1970, 1, 1)), time(12), timezone.utc).strftime("%Y-%m-%dT%H:%M:%S +0000")
        env.update(GIT_AUTHOR_DATE=timestamp, GIT_COMMITTER_DATE=timestamp)
        message = (record.get("message") or f"{row['trailer_instrument']} effective {effective}") + "\n\n"
        message += (f"Instrument: {row['trailer_instrument']}\nSource-url: {row['trailer_source_url']}\n"
                    f"In-force: {effective}\nKind: {record['kind']}\nLicence: {row['trailer_licence']}\n"
                    f"Jurisdiction: {row['iso2']}\nInstrument-id: {row['instrument_id']}")
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


if __name__ == "__main__":
    try:
        build(branch=sys.argv[sys.argv.index("--branch") + 1] if "--branch" in sys.argv else None)
    except (KeyError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
