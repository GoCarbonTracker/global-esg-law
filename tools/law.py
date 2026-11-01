#!/usr/bin/env python3
"""Ask what law applied on a date: python3 tools/law.py <ISO2> <YYYY-MM-DD> [--repo PATH] [--ref history] [--json]"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"Instrument": "title", "Source-url": "source_url", "In-force": "in_force", "Kind": "kind",
          "Licence": "licence", "Jurisdiction": "jurisdiction", "Instrument-id": "id"}


def _commits(repo, ref):
    out = subprocess.run(["git", "-C", str(repo), "log", "--first-parent", "--reverse",
                          "--format=%H%x1f%B%x1e", ref], check=True, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    for chunk in out.split("\x1e"):
        if not chunk.strip():
            continue
        sha, body = chunk.strip().split("\x1f", 1)
        trailers = {}
        for line in body.strip().split("\n\n")[-1].splitlines():
            key, _, value = line.partition(": ")
            if key in FIELDS:
                trailers[FIELDS[key]] = value
        if "in_force" in trailers:
            yield {**trailers, "commit": sha}


def _scope(repo, iso2):
    path = Path(repo) / "register" / iso2 / "scope.json"
    return {e["id"]: e for e in json.loads(path.read_text(encoding="utf-8"))} if path.exists() else {}


def known(repo=ROOT, ref="history"):
    registered = {p.parent.name for p in (Path(repo) / "register").glob("*/scope.json")}
    return sorted(registered | {c["jurisdiction"] for c in _commits(repo, ref) if "jurisdiction" in c})


def lookup(iso2, on, repo=ROOT, ref="history"):
    """Return (in_force list, not_yet list of {id, title, in_force}, first date or None)."""
    versions = sorted((c for c in _commits(repo, ref) if c.get("jurisdiction") == iso2),
                      key=lambda c: c["in_force"])  # sorted() is stable, so commit order breaks ties
    latest, pending = {}, {}
    for c in versions:
        if c["in_force"] <= on:
            latest[c["id"]] = c
        else:
            pending.setdefault(c["id"], c)
    scope = _scope(repo, iso2)
    keys = ("id", "title", "in_force", "kind", "source_url", "licence", "commit")
    found = []
    for c in sorted(latest.values(), key=lambda c: (c["in_force"], c["id"])):
        item = {k: c[k] for k in keys}
        note = scope.get(c["id"], {}).get("status_note")
        if note:
            item["status_note"] = note
        found.append(item)
    not_yet = [{k: c[k] for k in ("id", "title", "in_force")} for i, c in sorted(pending.items())
               if i not in latest]
    return found, not_yet, versions[0]["in_force"] if versions else None


def in_force(iso2, on, repo=ROOT, ref="history"):
    return lookup(iso2, on, repo, ref)[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("iso2")
    ap.add_argument("date")
    ap.add_argument("--repo", default=str(ROOT))
    ap.add_argument("--ref", default="history")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    iso2 = args.iso2.upper()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        print(f"malformed date {args.date!r}, expected YYYY-MM-DD", file=sys.stderr)
        return 2
    try:
        from datetime import date
        date.fromisoformat(args.date)
    except ValueError:
        print(f"malformed date {args.date!r}, expected YYYY-MM-DD", file=sys.stderr)
        return 2
    try:
        names = known(args.repo, args.ref)
        if iso2 not in names:
            print(f"unknown jurisdiction {iso2!r}; known: {', '.join(names)}", file=sys.stderr)
            return 2
        found, not_yet, first = lookup(iso2, args.date, args.repo, args.ref)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr.strip() or exc, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"jurisdiction": iso2, "date": args.date, "in_force": found, "not_yet_in_force": not_yet}, indent=2))
        return 0
    for item in found:
        print(f"{item['id']}\t{item['in_force']}\t{item['kind']}\t{item['title']}")
    for item in found:
        if "status_note" in item:
            print(f"note {item['id']}: {item['status_note']}")
    if not found:
        print(f"nothing in force before {first}" if first else f"no instruments stored for {iso2}")
    if not_yet:
        print("not yet in force")
        for item in not_yet:
            print(f"{item['id']}\t{item['in_force']}\t{item['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
