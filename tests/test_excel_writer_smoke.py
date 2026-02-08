from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from salud_tool.excel_writer import ExcelLayout, _format_sheet, write_doctor_xlsx


def test_write_doctor_xlsx_happy_path_and_formatting(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "date": [
                pd.to_datetime("2025-12-15").date(),
                pd.to_datetime("2025-12-16").date(),
            ],
            "datetime": [
                pd.Timestamp("2025-12-15 08:30", tz="UTC"),
                pd.Timestamp("2025-12-16 09:45", tz="UTC"),
            ],
            "glucose_count": [1, 2],
            "glucose_min": [100.0, 90.0],
            "glucose_max": [110.0, 120.0],
            "glucose_avg": [105.0, 100.0],
            "mmol_avg": [5.83, 5.55],
            "steps": [1000, 2000],
            "distance_m": [500.0, 1200.0],
            "calories_kcal": [120.0, 150.0],
            "active_minutes": [22.0, 18.0],
        }
    )
    out = tmp_path / "nested" / "out.xlsx"
    write_doctor_xlsx(df, out, ExcelLayout())

    wb = load_workbook(out)
    ws = cast(Worksheet, wb[ExcelLayout().sheet_name])

    headers = [cell.value for cell in ws[1]]
    assert headers[0] == "Día"
    assert "Fecha" in headers
    assert "Pasos" in headers
    assert "datetime" in headers

    assert ws.cell(row=2, column=1).value == "lun"
    dt_cell = ws.cell(row=2, column=headers.index("datetime") + 1).value
    assert isinstance(dt_cell, datetime)
    assert dt_cell.tzinfo is None

    assert ws.column_dimensions["A"].width == 6
    pasos_letter = get_column_letter(headers.index("Pasos") + 1)
    assert ws.column_dimensions[pasos_letter].width == 12

    pasos_cell = ws.cell(row=2, column=headers.index("Pasos") + 1)
    assert pasos_cell.number_format == "#,##0"
    gmin_cell = ws.cell(row=2, column=headers.index("Glucosa mín (mg/dL)") + 1)
    assert gmin_cell.number_format == "0.00"


def test_write_doctor_xlsx_raises_on_missing_date_value(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "date": [pd.to_datetime("2025-12-15").date(), None],
            "glucose_count": [1, 2],
        }
    )
    out = tmp_path / "out.xlsx"

    with pytest.raises(TypeError):
        write_doctor_xlsx(df, out, ExcelLayout())


def test_format_sheet_handles_missing_headers() -> None:
    wb = Workbook()
    ws = cast(Worksheet, wb.active)
    ws.append(["Solo"])
    ws.append([1])

    _format_sheet(ws)

    assert ws.cell(row=1, column=1).font.bold is True
    assert ws.cell(row=2, column=1).alignment.horizontal == "center"
