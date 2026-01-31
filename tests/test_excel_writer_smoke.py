from __future__ import annotations

from pathlib import Path

import pandas as pd

from salud_tool.excel_writer import ExcelLayout, write_doctor_xlsx


def test_excel_writer_creates_file(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "date": [pd.to_datetime("2025-12-15").date()],
            "glucose_count": [1],
            "glucose_min": [100.0],
            "glucose_max": [110.0],
            "glucose_avg": [105.0],
            "mmol_avg": [5.83],
            "steps": [1000],
            "distance_m": [500.0],
            "calories_kcal": [120.0],
            "active_minutes": [22.0],
        }
    )
    out = tmp_path / "out.xlsx"
    write_doctor_xlsx(df, out, ExcelLayout())
    assert out.exists()
    assert out.stat().st_size > 0
