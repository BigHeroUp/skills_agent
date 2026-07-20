from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError

import pytest

from services.knowledge_graph.domain import RawReadStatus
from services.knowledge_graph.validation import RawGraphDocumentReader
from services.knowledge_graph.validation import reader as reader_module


def test_reader_preserves_text_and_builds_path_independent_raw_fingerprint(tmp_path):
    payload = '{"schema_version": 1, "nodes": [], "edges": []}\n'
    first = tmp_path / "first" / "knowledge_graph.json"
    second = tmp_path / "second" / "knowledge_graph.json"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text(payload, encoding="utf-8")
    second.write_text(payload, encoding="utf-8")

    left = RawGraphDocumentReader().read(first)
    right = RawGraphDocumentReader().read(second)

    assert left.status == RawReadStatus.VALID
    assert left.original_text == payload
    assert left.original_bytes == payload.encode("utf-8")
    assert left.source_name == "knowledge_graph.json"
    assert left.fingerprint.value == hashlib.sha256(payload.encode()).hexdigest()
    assert left.fingerprint == right.fingerprint
    with pytest.raises(FrozenInstanceError):
        left.source_name = "changed.json"


def test_reader_handles_missing_empty_corrupt_and_non_object_documents(tmp_path):
    missing = RawGraphDocumentReader().read(tmp_path / "missing.json")
    empty_path = tmp_path / "empty.json"
    empty_path.write_text("  \n", encoding="utf-8")
    empty = RawGraphDocumentReader().read(empty_path)
    corrupt_path = tmp_path / "corrupt.json"
    corrupt_path.write_text("{invalid", encoding="utf-8")
    corrupt = RawGraphDocumentReader().read(corrupt_path)
    array_path = tmp_path / "array.json"
    array_path.write_text("[]", encoding="utf-8")
    non_object = RawGraphDocumentReader().read(array_path)

    assert missing.status == RawReadStatus.MISSING
    assert missing.fingerprint is None
    assert not (tmp_path / "missing.json").exists()
    assert empty.status == RawReadStatus.EMPTY
    assert empty.fingerprint is not None
    assert corrupt.status == RawReadStatus.CORRUPT
    assert corrupt.parse_issues[0].code == "raw.json_syntax_error"
    assert non_object.status == RawReadStatus.NON_OBJECT


def test_reader_handles_expected_os_error_without_traceback(tmp_path, monkeypatch):
    path = tmp_path / "unreadable.json"
    path.write_text("{}", encoding="utf-8")

    def deny_read(self):
        raise PermissionError("denied")

    monkeypatch.setattr(reader_module.Path, "read_bytes", deny_read)
    document = RawGraphDocumentReader().read(path)

    assert document.status == RawReadStatus.UNREADABLE
    assert document.parse_issues[0].code == "raw.file_unreadable"
    assert document.parse_issues[0].evidence["error_type"] == "PermissionError"


def test_reader_preserves_original_bytes_when_utf8_is_invalid(tmp_path):
    path = tmp_path / "invalid_utf8.json"
    payload = b'{"schema_version":1,"nodes":[],' + bytes([0xFF]) + b'"edges":[]}'
    path.write_bytes(payload)

    document = RawGraphDocumentReader().read(path)

    assert document.status == RawReadStatus.CORRUPT
    assert document.original_bytes == payload
    assert document.fingerprint.value == hashlib.sha256(payload).hexdigest()
    assert document.parse_issues[0].code == "raw.invalid_utf8"


def test_reader_detects_duplicate_keys_with_precise_best_effort_pointer(tmp_path):
    path = tmp_path / "duplicate_keys.json"
    path.write_text(
        '{"schema_version":1,"nodes":[{"id":"first","id":"second",'
        '"type":"dataset","label":"D","properties":{}}],"edges":[]}',
        encoding="utf-8",
    )

    document = RawGraphDocumentReader().read(path)

    assert document.status == RawReadStatus.VALID
    assert document.duplicate_keys[0].key == "id"
    assert document.duplicate_keys[0].location == "/nodes/0/id"
    assert "\"id\":\"first\",\"id\":\"second\"" in document.original_text


@pytest.mark.parametrize(
    ("raw", "expected_locations"),
    [
        (
            '{"schema_version":1,"nodes":[],"nodes":[],"edges":[]}',
            ["/nodes"],
        ),
        (
            '{"schema_version":1,"nodes":[{"id":"a","id":"b"}],"edges":[]}',
            ["/nodes/0/id"],
        ),
        (
            '{"schema_version":1,"nodes":[],"edges":[{"source":"a","source":"b"}]}',
            ["/edges/0/source"],
        ),
        (
            '{"schema_version":1,"nodes":[{"properties":{"name":"a","name":"b"}}],"edges":[]}',
            ["/nodes/0/properties/name"],
        ),
        (
            '{"schema_version":1,"nodes":[{"properties":{"nested":{"key":1,"key":2}}}],"edges":[]}',
            ["/nodes/0/properties/nested/key"],
        ),
        (
            '{"schema_version":1,"nodes":[{"id":"a","id":"b","id":"c","type":"x","type":"y"}],"edges":[]}',
            ["/nodes/0/id", "/nodes/0/id", "/nodes/0/type"],
        ),
        (
            '{"schema_version":1,"nodes":[{"label":"a","label":"b"},{"label":"c","label":"d"}],"edges":[]}',
            ["/nodes/0/label", "/nodes/1/label"],
        ),
    ],
)
def test_reader_keeps_every_duplicate_key_observable(tmp_path, raw, expected_locations):
    path = tmp_path / "duplicates.json"
    path.write_text(raw, encoding="utf-8")

    document = RawGraphDocumentReader().read(path)

    assert [item.location for item in document.duplicate_keys] == expected_locations


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_reader_tracks_non_finite_json_constants(tmp_path, constant):
    path = tmp_path / f"{constant}.json"
    path.write_text(
        '{"schema_version":1,"nodes":[{"id":"dataset:1","type":"dataset",'
        '"label":"D","properties":{"row_count":'
        + constant
        + '}}],"edges":[]}',
        encoding="utf-8",
    )

    document = RawGraphDocumentReader().read(path)

    assert document.non_finite_numbers[0].value == constant
    assert document.non_finite_numbers[0].location == "/nodes/0/properties/row_count"
