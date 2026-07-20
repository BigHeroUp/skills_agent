from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import validate_knowledge_graph as cli


FIXTURES = Path(__file__).parent / "fixtures" / "knowledge_graph"


def test_cli_text_and_json_outputs(capsys):
    text_code = cli.main(["--path", str(FIXTURES / "v1_valid.json"), "--format", "text"])
    text_output = capsys.readouterr().out
    json_code = cli.main(["--path", str(FIXTURES / "v1_valid.json"), "--format", "json"])
    json_output = capsys.readouterr().out

    assert text_code == 0
    assert "Status: valid" in text_output
    assert json_code == 0
    assert json.loads(json_output)["report"]["status"] == "valid"


def test_cli_json_output_is_byte_for_byte_deterministic(capsys):
    args = ["--path", str(FIXTURES / "v1_legacy.json"), "--format", "json"]

    first_code = cli.main(args)
    first_output = capsys.readouterr().out
    second_code = cli.main(args)
    second_output = capsys.readouterr().out

    assert first_code == second_code == 0
    assert first_output == second_output
    assert json.loads(first_output)["report"]["status"] == "degraded"


def test_cli_exit_codes_are_stable(tmp_path, capsys):
    invalid = tmp_path / "invalid.json"
    invalid.write_text("[]", encoding="utf-8")
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{bad", encoding="utf-8")
    future = tmp_path / "future.json"
    future.write_text('{"schema_version":2,"nodes":[],"edges":[]}', encoding="utf-8")

    assert cli.main(["--path", str(invalid)]) == 1
    capsys.readouterr()
    assert cli.main(["--path", str(corrupt)]) == 2
    capsys.readouterr()
    assert cli.main(["--path", str(future)]) == 3


def test_cli_does_not_modify_file_content_mtime_or_fingerprint(tmp_path, capsys):
    path = tmp_path / "knowledge_graph.json"
    original = (FIXTURES / "v1_valid.json").read_bytes()
    path.write_bytes(original)
    before_stat = path.stat()
    before_hash = hashlib.sha256(path.read_bytes()).hexdigest()

    exit_code = cli.main(["--path", str(path), "--format", "json", "--mode", "strict"])
    capsys.readouterr()

    assert exit_code == 0
    assert path.read_bytes() == original
    assert path.stat().st_mtime_ns == before_stat.st_mtime_ns
    assert path.stat().st_size == before_stat.st_size
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before_hash


def test_cli_missing_file_does_not_create_it(tmp_path, capsys):
    path = tmp_path / "missing.json"

    exit_code = cli.main(["--path", str(path)])
    output = capsys.readouterr().out

    assert exit_code == 2
    assert "Status: unreadable" in output
    assert not path.exists()


def test_cli_relative_and_absolute_paths_have_same_private_output(tmp_path, monkeypatch, capsys):
    path = tmp_path / "knowledge_graph.json"
    path.write_bytes((FIXTURES / "v1_valid.json").read_bytes())
    monkeypatch.chdir(tmp_path)

    relative_code = cli.main(["--path", path.name, "--format", "json"])
    relative_output = capsys.readouterr().out
    absolute_code = cli.main(["--path", str(path.resolve()), "--format", "json"])
    absolute_output = capsys.readouterr().out

    assert relative_code == absolute_code == 0
    assert relative_output == absolute_output
    assert str(tmp_path) not in relative_output
