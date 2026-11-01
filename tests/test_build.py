import json
import subprocess
from datetime import date
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build


def fixture(repo):
    (repo / "records" / "EU" / "law").mkdir(parents=True)
    (repo / "records" / "EU" / "law2").mkdir(parents=True)
    rows = [
        {"id": "old", "verdict": "pass", "form": "adopted", "publisher": "P", "source_name": "S", "trailer_instrument": "Old Act", "trailer_source_url": "https://example.org/old", "trailer_licence": "CC0"},
        {"id": "new", "verdict": "pass", "form": "adopted", "publisher": "P", "source_name": "S", "trailer_instrument": "New Act", "trailer_source_url": "https://example.org/new", "trailer_licence": "OGL"},
    ]
    (repo / "sources.json").write_text(json.dumps(rows))
    (repo / "register" / "EU").mkdir(parents=True)
    (repo / "register" / "EU" / "scope.json").write_text(json.dumps([
        {"id": "law", "title": "Scope Title", "official_url": "https://example.org/scope", "source_row": "old"},
        {"id": "law2", "title": "Scope Title", "official_url": "https://example.org/scope", "source_row": "new"}]))
    for name, source, effective in [("old", "old", "1965-01-02"), ("new", "new", "2020-03-04")]:
        (repo / "records" / "EU" / ("law" if name == "old" else "law2") / f"{name}.json").write_text(json.dumps({"source_id": source, "in_force": effective, "kind": "adopted", "text": name}))
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.org"], check=True)


def test_build_trailers_order_and_rebuild(tmp_path):
    histories = []
    for name in ("one", "two"):
        repo = tmp_path / name
        repo.mkdir()
        fixture(repo)
        assert build.build(repo) == [("1965-01-02", "Scope Title"), ("2020-03-04", "Scope Title")]
        commits = subprocess.check_output(["git", "-C", str(repo), "log", "--reverse", "--format=%H"], text=True).splitlines()
        history = []
        for commit in commits:
            body = subprocess.check_output(["git", "-C", str(repo), "show", "-s", "--format=%B", commit], text=True)
            trailers = dict(line.split(": ", 1) for line in body.splitlines() if ": " in line)
            assert {"Instrument", "Source-url", "In-force", "Kind", "Licence", "Jurisdiction", "Instrument-id"} <= trailers.keys()
            assert (trailers["Jurisdiction"], trailers["Instrument-id"]) == ("EU", "law" if trailers["In-force"] == "1965-01-02" else "law2")
            history.append((trailers["In-force"], trailers["Instrument"]))
        assert history == [("1965-01-02", "Scope Title"), ("2020-03-04", "Scope Title")]
        histories.append(history)
    assert histories[0] == histories[1]


def test_branch_build_is_orphan_and_rebuild_equal(tmp_path):
    fixture(tmp_path)
    def snapshot():
        log = subprocess.check_output(["git", "-C", str(tmp_path), "log", "--first-parent", "--reverse", "--format=%an|%ad|%B", "--date=iso-strict", "history"], text=True)
        tree = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "history^{tree}"], text=True)
        return log, tree
    build.build(tmp_path, branch="history")
    first = snapshot()
    build.build(tmp_path, branch="history")
    assert snapshot() == first
    assert subprocess.check_output(["git", "-C", str(tmp_path), "rev-list", "--count", "history"], text=True).strip() == "2"
    assert subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], capture_output=True).returncode != 0  # nothing committed on the current branch
    assert subprocess.check_output(["git", "-C", str(tmp_path), "show", "history:records/EU/law/old.json"], text=True)
    assert subprocess.check_output(["git", "-C", str(tmp_path), "status", "--porcelain"], text=True) == "?? records/\n?? register/\n?? sources.json\n"


def test_trailers_come_from_scope_json(tmp_path):
    fixture(tmp_path)
    build.build(tmp_path)
    body = subprocess.check_output(["git", "-C", str(tmp_path), "log", "-1", "--format=%B"], text=True)
    assert "Instrument: Scope Title" in body and "Source-url: https://example.org/scope" in body
    assert "Licence: OGL" in body


def test_build_refuses_instrument_missing_from_scope(tmp_path):
    fixture(tmp_path)
    (tmp_path / "register" / "EU" / "scope.json").write_text("[]")
    try:
        build.build(tmp_path)
    except ValueError as exc:
        assert "scope.json" in str(exc)
    else:
        raise AssertionError("record without scope entry was accepted")


def test_build_refuses_nonpass_row(tmp_path):
    repo = tmp_path / "blocked"
    repo.mkdir()
    fixture(repo)
    rows = json.loads((repo / "sources.json").read_text())
    rows[0]["verdict"] = "unknown"
    (repo / "sources.json").write_text(json.dumps(rows))
    try:
        build.build(repo)
    except ValueError as exc:
        assert "old" in str(exc)
    else:
        raise AssertionError("non-pass source row was accepted")


def test_pilot_scope_lists_match_sources_and_register():
    import csv
    rows = {r["id"]: r for r in json.loads((ROOT / "sources.json").read_text())}
    register = {(r["iso2"], r["official_source_url"], r["law_family"]) for r in csv.DictReader((ROOT / "register" / "register.csv").open(encoding="utf-8"))}
    for iso2 in ("EU", "GB", "IN", "US"):
        entries = json.loads((ROOT / "register" / iso2 / "scope.json").read_text())
        assert len({e["id"] for e in entries}) == len(entries)
        for e in entries:
            assert e["status"] in ("stored", "link only", "pending")
            ids = e["source_row"] if isinstance(e["source_row"], list) else [e["source_row"]]
            assert (e["status"] == "link only") == (any(rows[i]["verdict"] != "pass" for i in ids))
            assert e["law_family"] in ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
            assert (iso2, e["official_url"], e["law_family"]) in register
            assert e["in_force"] is None or date.fromisoformat(e["in_force"])
