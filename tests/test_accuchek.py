from __future__ import annotations

import json
from pathlib import Path

from salud_tool.sources.accuchek import AccuChekPaths, AccuChekSource


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
