from __future__ import annotations

import json
from pathlib import Path

import pytest

from salud_tool.sources.accuchek import (
    AccuChekPaths,
    AccuChekSource,
    _extract_json_list,
    _parse_timestamp,
)


def test_accuchek_parses_list(tmp_path: Path) -> None:
    data = [
        {"timestamp": "2026/01/31 11:57", "mg/dL": 119, "mmol/L": 6.611111},
        {"epoch": 1769774400, "mg/dL": 118, "mmol/L": 6.555556},
    ]
    p = tmp_path / "accuchek_2026-01-31_11-57-00.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    readings = src.load_readings(p)

    assert len(readings) == 2
    assert readings[0].mg_dl == 118.0 or readings[0].mg_dl == 119.0


def test_validate_raises_when_root_missing(tmp_path: Path) -> None:
    missing = tmp_path / "noexiste"
    src = AccuChekSource(AccuChekPaths(root=missing))
    with pytest.raises(FileNotFoundError, match=str(missing)):
        src.validate()


def test_validate_succeeds_when_root_exists(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    src.validate()


def test_newest_json_raises_when_no_files(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    with pytest.raises(FileNotFoundError, match="No accuchek_"):
        src.newest_json()


def test_newest_json_returns_only_file(tmp_path: Path) -> None:
    p = tmp_path / "accuchek_2026-01-31.json"
    p.write_text("[]", encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    assert src.newest_json() == p


def test_newest_json_returns_newest_by_mtime(tmp_path: Path) -> None:
    old_f = tmp_path / "accuchek_old.json"
    new_f = tmp_path / "accuchek_new.json"
    old_f.write_text("[]", encoding="utf-8")
    new_f.write_text("[]", encoding="utf-8")
    old_f.touch()
    new_f.touch()
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    got = src.newest_json()
    assert got in (old_f, new_f)
    assert got.name.startswith("accuchek_")


def test_load_readings_invalid_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    with pytest.raises(json.JSONDecodeError):
        src.load_readings(p)


def test_load_readings_not_list_raises(tmp_path: Path) -> None:
    p = tmp_path / "obj.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    with pytest.raises(ValueError, match="must be a list"):
        src.load_readings(p)


def test_load_readings_skips_non_dict_items(tmp_path: Path) -> None:
    p = tmp_path / "mixed.json"
    data = [
        {"timestamp": "2026/01/31 08:00", "mg/dL": 100, "mmol/L": 5.55},
        "string",
        42,
        None,
    ]
    p.write_text(json.dumps(data), encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    readings = src.load_readings(p)
    assert len(readings) == 1
    assert readings[0].mg_dl == 100.0


def test_load_readings_skips_missing_mg_dl_or_mmol_l(tmp_path: Path) -> None:
    p = tmp_path / "partial.json"
    data = [
        {"timestamp": "2026/01/31 08:00", "mmol/L": 5.55},
        {"timestamp": "2026/01/31 09:00", "mg/dL": 110},
    ]
    p.write_text(json.dumps(data), encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    readings = src.load_readings(p)
    assert len(readings) == 0


def test_load_readings_missing_timestamp_and_epoch_raises(tmp_path: Path) -> None:
    p = tmp_path / "no_ts.json"
    data = [{"mg/dL": 100, "mmol/L": 5.55}]
    p.write_text(json.dumps(data), encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    with pytest.raises(ValueError, match="Missing timestamp"):
        src.load_readings(p)


def test_load_readings_parses_timestamp_string(tmp_path: Path) -> None:
    p = tmp_path / "ts_str.json"
    data = [{"timestamp": "2026/01/31 11:57", "mg/dL": 119, "mmol/L": 6.6}]
    p.write_text(json.dumps(data), encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    readings = src.load_readings(p)
    assert len(readings) == 1
    assert readings[0].mg_dl == 119.0
    assert readings[0].timestamp.strftime("%Y/%m/%d %H:%M") == "2026/01/31 11:57"


def test_load_readings_parses_epoch_when_no_timestamp(tmp_path: Path) -> None:
    p = tmp_path / "epoch.json"
    data = [{"epoch": 1769774400, "mg/dL": 118, "mmol/L": 6.55}]
    p.write_text(json.dumps(data), encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    readings = src.load_readings(p)
    assert len(readings) == 1
    assert readings[0].mg_dl == 118.0


def test_load_readings_empty_list_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "empty.json"
    p.write_text("[]", encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    assert src.load_readings(p) == []


def test_load_readings_sorts_by_timestamp(tmp_path: Path) -> None:
    p = tmp_path / "unsorted.json"
    data = [
        {"timestamp": "2026/01/31 14:00", "mg/dL": 120, "mmol/L": 6.66},
        {"timestamp": "2026/01/31 08:00", "mg/dL": 95, "mmol/L": 5.27},
    ]
    p.write_text(json.dumps(data), encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    readings = src.load_readings(p)
    assert [r.mg_dl for r in readings] == [95.0, 120.0]


def test_parse_timestamp_from_string() -> None:
    ts = _parse_timestamp("2026/01/31 11:57", None)
    assert ts.strftime("%Y/%m/%d %H:%M") == "2026/01/31 11:57"
    assert ts.tzinfo is not None


def test_parse_timestamp_from_epoch() -> None:
    ts = _parse_timestamp(None, 1769774400)
    assert ts.tzinfo is not None


def test_parse_timestamp_empty_string_uses_epoch() -> None:
    ts = _parse_timestamp("", 1769774400)
    assert ts.tzinfo is not None


def test_parse_timestamp_missing_both_raises() -> None:
    with pytest.raises(ValueError, match="Missing timestamp"):
        _parse_timestamp(None, None)


def test_load_readings_parses_tag_when_present(tmp_path: Path) -> None:
    p = tmp_path / "with_tag.json"
    data = [
        {
            "timestamp": "2026/01/31 08:00",
            "mg/dL": 100,
            "mmol/L": 5.55,
            "tag": "Antes comida",
        },
        {
            "timestamp": "2026/01/31 14:00",
            "mg/dL": 118,
            "mmol/L": 6.55,
            "tag": "Desp. Comida",
        },
    ]
    p.write_text(json.dumps(data), encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    readings = src.load_readings(p)
    assert len(readings) == 2
    assert readings[0].tag == "Antes comida"
    assert readings[1].tag == "Desp. Comida"


def test_load_readings_tag_optional_without_key(tmp_path: Path) -> None:
    p = tmp_path / "no_tag.json"
    data = [{"timestamp": "2026/01/31 08:00", "mg/dL": 100, "mmol/L": 5.55}]
    p.write_text(json.dumps(data), encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    readings = src.load_readings(p)
    assert len(readings) == 1
    assert readings[0].tag is None


def test_load_readings_tag_empty_string_becomes_none(tmp_path: Path) -> None:
    p = tmp_path / "empty_tag.json"
    data = [{"timestamp": "2026/01/31 08:00", "mg/dL": 100, "mmol/L": 5.55, "tag": ""}]
    p.write_text(json.dumps(data), encoding="utf-8")
    src = AccuChekSource(AccuChekPaths(root=tmp_path))
    readings = src.load_readings(p)
    assert readings[0].tag is None


def test_extract_json_list_pure_json() -> None:
    raw = _extract_json_list("[1, 2, 3]")
    assert raw == [1, 2, 3]


def test_extract_json_list_with_leading_garbage() -> None:
    text = (
        "0.594510(   +0.000000):info: running as non-root\n"
        '[{"mg/dL": 100, "mmol/L": 5.55}]'
    )
    raw = _extract_json_list(text)
    assert isinstance(raw, list)
    assert len(raw) == 1
    assert raw[0]["mg/dL"] == 100
