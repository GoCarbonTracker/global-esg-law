#!/usr/bin/env python3
"""Copy a merged CSV register into register/register.csv."""
import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"iso2", "country", "law_family", "duty_on", "tier_hint", "verification"}


def main(source):
    source = Path(source)
    with source.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED - set(reader.fieldnames or ())
        if missing:
            raise ValueError("missing required columns: " + ", ".join(sorted(missing)))
        rows = list(reader)
    target = ROOT / "register" / "register.csv"
    if target.exists():
        raise SystemExit(f"{target} exists; refusing to overwrite (it holds per-instrument rows the seed lacks)")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=reader.fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: tools/seed_register.py <path-to-merged-csv>")
    main(sys.argv[1])
