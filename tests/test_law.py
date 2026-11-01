import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build
import law
from test_build import fixture


def make(tmp_path, extra=()):
    fixture(tmp_path)
    scope = tmp_path / "register" / "EU" / "scope.json"
    entries = json.loads(scope.read_text())
    entries[1]["status_note"] = "stayed by a court"
    scope.write_text(json.dumps(entries))
    for name, effective in extra:  # a second version of law2
        (tmp_path / "records" / "EU" / "law2" / f"{name}.json").write_text(json.dumps(
            {"source_id": "new", "in_force": effective, "kind": "adopted", "text": name}))
    build.build(tmp_path, branch="history")
    return tmp_path


def ids(found):
    return [i["id"] for i in found]


def test_lookups_before_between_after(tmp_path):
    repo = make(tmp_path)
    assert law.in_force("EU", "1960-01-01", repo) == []
    assert ids(law.in_force("EU", "1965-01-02", repo)) == ["law"]
    assert ids(law.in_force("EU", "2000-01-01", repo)) == ["law"]
    found = law.in_force("EU", "2021-01-01", repo)
    assert ids(found) == ["law", "law2"]
    assert set(found[0]) == {"id", "title", "in_force", "kind", "source_url", "licence", "commit"}


def test_latest_version_wins(tmp_path):
    repo = make(tmp_path, [("newer", "2022-01-01")])
    by_id = {i["id"]: i for i in law.in_force("EU", "2023-01-01", repo)}
    assert by_id["law2"]["in_force"] == "2022-01-01"
    assert {i["id"]: i for i in law.in_force("EU", "2021-01-01", repo)}["law2"]["in_force"] == "2020-03-04"


def test_status_note_passthrough(tmp_path):
    repo = make(tmp_path)
    by_id = {i["id"]: i for i in law.in_force("EU", "2021-01-01", repo)}
    assert by_id["law2"]["status_note"] == "stayed by a court"
    assert "status_note" not in by_id["law"]


def commit_on_history(repo, message, *extra_parents):
    git = lambda *a: subprocess.check_output(["git", "-C", str(repo), "-c", "user.name=T", "-c", "user.email=t@x.org", *a], text=True).strip()
    tree = git("rev-parse", "history^{tree}")
    sha = git("commit-tree", tree, "-p", "history", *[x for p in extra_parents for x in ("-p", p)], "-m", message)
    git("update-ref", "refs/heads/history", sha)


def test_first_parent_walk_ignores_side_branch(tmp_path):
    repo = make(tmp_path)
    git = lambda *a: subprocess.check_output(["git", "-C", str(repo), "-c", "user.name=T", "-c", "user.email=t@x.org", *a], text=True).strip()
    tree = git("rev-parse", "history^{tree}")
    side = git("commit-tree", tree, "-m", "side\n\nInstrument: Ghost\nIn-force: 1900-01-01\nKind: adopted\nJurisdiction: EU\nInstrument-id: ghost")
    commit_on_history(repo, "merge", side)
    assert ids(law.in_force("EU", "2021-01-01", repo)) == ["law", "law2"]


def test_in_force_order_beats_commit_order(tmp_path):
    repo = make(tmp_path)
    commit_on_history(repo, "late commit\n\nInstrument: Old Act\nSource-url: u\nIn-force: 1990-01-01\nKind: adopted\nLicence: CC0\nJurisdiction: EU\nInstrument-id: law")
    found = {i["id"]: i for i in law.in_force("EU", "2021-01-01", repo)}
    assert found["law"]["in_force"] == "1990-01-01"  # last in commit order, latest by In-force
    assert law.in_force("EU", "1980-01-01", repo)[0]["in_force"] == "1965-01-02"
    commit_on_history(repo, "backfill\n\nInstrument: New Act\nIn-force: 2010-01-01\nKind: adopted\nJurisdiction: EU\nInstrument-id: law2")
    found = {i["id"]: i for i in law.in_force("EU", "2021-01-01", repo)}
    assert found["law2"]["in_force"] == "2020-03-04"  # added last, but dated earlier


def test_not_yet_in_force_and_cli(tmp_path, capsys):
    repo = make(tmp_path)
    assert law.main(["EU", "2000-01-01", "--repo", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "law\t1965-01-02" in out and "not yet in force" in out and "law2\t2020-03-04" in out
    assert law.main(["EU", "1960-01-01", "--repo", str(repo)]) == 0
    assert "nothing in force before 1965-01-02" in capsys.readouterr().out
    assert law.main(["EU", "2021-01-01", "--repo", str(repo)]) == 0
    assert "note law2: stayed by a court" in capsys.readouterr().out
    assert law.main(["EU", "1960-01-01", "--repo", str(repo), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["not_yet_in_force"][0]["id"] == "law"


def test_unknown_jurisdiction_and_bad_date(tmp_path, capsys):
    repo = make(tmp_path)
    assert law.main(["ZZ", "2020-01-01", "--repo", str(repo)]) == 2
    assert "EU" in capsys.readouterr().err
    for bad in ("2020-13-01", "2020-1-1", "yesterday"):
        assert law.main(["EU", bad, "--repo", str(repo)]) == 2


def test_pre_1970_date(tmp_path):
    repo = make(tmp_path)
    assert ids(law.in_force("EU", "1969-12-31", repo)) == ["law"]
