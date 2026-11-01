import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import publish_gate


def make(repo, status="stored", verdict="pass", records=1, source_row="R1"):
    (repo / "sources.json").write_text(json.dumps([{"id": "R1", "verdict": verdict}]))
    (repo / "register" / "XX").mkdir(parents=True)
    (repo / "register" / "XX" / "scope.json").write_text(json.dumps([
        {"id": "act", "status": status, "source_row": source_row}]))
    folder = repo / "records" / "XX" / "act"
    folder.mkdir(parents=True)
    for i in range(records):
        (folder / f"{i}.json").write_text("{}")


def refusals(repo):
    report, bad = publish_gate.gate(repo)
    assert any("source R1" in line for line in report) and any("XX/act" in line for line in report)
    return bad


def test_pass(tmp_path):
    make(tmp_path)
    assert refusals(tmp_path) == []


def test_link_only_without_records_passes(tmp_path):
    make(tmp_path, status="link only", records=0)
    assert refusals(tmp_path) == []


def test_pending(tmp_path):
    make(tmp_path, status="pending", records=0)
    assert "pending" in refusals(tmp_path)[0]


def test_stored_without_record(tmp_path):
    make(tmp_path, records=0)
    assert "no record" in refusals(tmp_path)[0]


def test_stored_with_non_pass_row(tmp_path):
    make(tmp_path, verdict="permission requested")
    assert "not 'pass'" in refusals(tmp_path)[0]


def test_link_only_with_records(tmp_path):
    make(tmp_path, status="link only")
    assert "link only but has 1" in refusals(tmp_path)[0]
