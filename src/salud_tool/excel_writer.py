"""Generación de Excel formateado para entrega médica."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl.styles import Alignment, Border, Font, Side

_DIA_SEMANA: tuple[str, ...] = ("lun", "mar", "mie", "jue", "vie", "sab", "dom")

_HEADER_MAP: dict[str, str] = {
    "weekday": "Día",
    "date": "Fecha",
    "glucose_count": "Mediciones (n)",
    "glucose_min": "Glucosa mín (mg/dL)",
    "glucose_max": "Glucosa máx (mg/dL)",
    "glucose_avg": "Glucosa prom (mg/dL)",
    "mmol_avg": "Glucosa prom (mmol/L)",
    "steps": "Pasos",
    "distance_m": "Distancia (m)",
    "calories_kcal": "Calorías (kcal)",
    "active_minutes": "Minutos activos",
}


@dataclass(frozen=True)
class ExcelLayout:
    """Layout/formatting configuration for the doctor sheet."""

    sheet_name: str = "Consolidado diario"


def write_doctor_xlsx(df: pd.DataFrame, out_path: Path, layout: ExcelLayout) -> None:
    """Write a formatted Excel file suitable for printing.

    Args:
        df: Consolidated daily DataFrame.
        out_path: Output path for the XLSX file.
        layout: Excel layout parameters.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    export_df = df.copy()

    # Excel/openpyxl cannot write timezone-aware datetimes.
    if "date" in export_df.columns:
        export_df["weekday"] = pd.to_datetime(export_df["date"]).dt.weekday
        export_df["weekday"] = export_df["weekday"].map(
            lambda i: _DIA_SEMANA[i] if 0 <= i < 7 else ""
        )
        cols = ["weekday"] + [c for c in export_df.columns if c != "weekday"]
        export_df = export_df[cols]

    # Excel/openpyxl cannot write timezone-aware datetimes.
    if "datetime" in export_df.columns:
        export_df["datetime"] = pd.to_datetime(
            export_df["datetime"], errors="coerce"
        ).dt.tz_localize(None)

    # User-facing headers in Spanish
    export_df = export_df.rename(columns=_HEADER_MAP)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name=layout.sheet_name)
        ws = writer.book[layout.sheet_name]
        _format_sheet(ws)


def _format_sheet(ws: Any) -> None:
    """Apply borders, widths and number formats to a worksheet.

    Args:
        ws: openpyxl worksheet.
    """
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    header_font = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Header row
    for cell in ws[1]:
        cell.font = header_font
        cell.alignment = center
        cell.border = border

    # Body
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = center
            cell.border = border

    headers = [str(cell.value) for cell in ws[1]]
    col_index = {name: idx + 1 for idx, name in enumerate(headers)}

    def set_col_width(header: str, width: float) -> None:
        idx = col_index.get(header)
        if idx is None:
            return
        letter = ws.cell(row=1, column=idx).column_letter
        ws.column_dimensions[letter].width = width

    # Widths (avoid ###)
    set_col_width("Día", 6)
    set_col_width("Fecha", 12)
    set_col_width("Mediciones (n)", 14)
    set_col_width("Glucosa mín (mg/dL)", 16)
    set_col_width("Glucosa máx (mg/dL)", 16)
    set_col_width("Glucosa prom (mg/dL)", 18)
    set_col_width("Glucosa prom (mmol/L)", 18)
    set_col_width("Pasos", 12)
    set_col_width("Distancia (m)", 14)
    set_col_width("Calorías (kcal)", 16)
    set_col_width("Minutos activos", 16)

    fmt_map: dict[str, str] = {
        "Mediciones (n)": "0",
        "Glucosa mín (mg/dL)": "0.00",
        "Glucosa máx (mg/dL)": "0.00",
        "Glucosa prom (mg/dL)": "0.00",
        "Glucosa prom (mmol/L)": "0.00",
        "Pasos": "#,##0",
        "Distancia (m)": "#,##0.00",
        "Calorías (kcal)": "#,##0.00",
        "Minutos activos": "0",
    }

    for row in ws.iter_rows(min_row=2):
        for header, fmt in fmt_map.items():
            idx = col_index.get(header)
            if idx is None:
                continue
            row[idx - 1].number_format = fmt
