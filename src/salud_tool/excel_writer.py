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
    "datetime": "Fecha / Hora",
    "glucose_mg_dl": "Glucosa (mg/dL)",
    "steps": "Pasos",
    "distance_m": "Distancia (m)",
    "calories_kcal": "Calorías\n(kcal)",
    "active_minutes": "Minutos\nactivos",
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

    # Día de la semana desde date o datetime
    if "date" in export_df.columns:
        weekday_series = pd.to_datetime(export_df["date"]).dt.weekday
    elif "datetime" in export_df.columns:
        weekday_series = pd.to_datetime(export_df["datetime"]).dt.weekday
    else:
        weekday_series = pd.Series(dtype=object)

    if not weekday_series.empty:

        def _weekday_label(i: object) -> str:
            try:
                if i is None or (isinstance(i, float) and pd.isna(i)):
                    return ""
                if isinstance(i, int | float):
                    idx = int(i)
                    return _DIA_SEMANA[idx] if 0 <= idx < 7 else ""
                return ""
            except (ValueError, TypeError):
                return ""

        export_df["weekday"] = weekday_series.map(_weekday_label)
        cols = ["weekday"] + [c for c in export_df.columns if c != "weekday"]
        export_df = export_df[cols]

    # Fecha con hora: usar datetime y quitar date; Excel sin timezone
    if "datetime" in export_df.columns:
        export_df["datetime"] = pd.to_datetime(
            export_df["datetime"], errors="coerce"
        ).dt.tz_localize(None)
    if "date" in export_df.columns:
        export_df = export_df.drop(columns=["date"])

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

    # Header row (wrap_text ya en center)
    for cell in ws[1]:
        cell.font = header_font
        cell.alignment = center
        cell.border = border

    # Body: alineación y altura reducida
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = center
            cell.border = border
        ws.row_dimensions[row[0].row].height = 15

    headers = [str(cell.value) for cell in ws[1]]
    col_index = {name: idx + 1 for idx, name in enumerate(headers)}

    def set_col_width(header: str, width: float) -> None:
        idx = col_index.get(header)
        if idx is None:
            return
        letter = ws.cell(row=1, column=idx).column_letter
        ws.column_dimensions[letter].width = width

    # Widths (evitar ###; Fecha / Hora más ancha; Calorías y Minutos en 2 líneas)
    set_col_width("Día", 6)
    set_col_width("Fecha / Hora", 18)
    set_col_width("Glucosa (mg/dL)", 14)
    set_col_width("Pasos", 12)
    set_col_width("Distancia (m)", 14)
    set_col_width("Calorías\n(kcal)", 10)
    set_col_width("Minutos\nactivos", 10)

    fmt_map: dict[str, str] = {
        "Fecha / Hora": "dd/mm/yyyy hh:mm",
        "Glucosa (mg/dL)": "0.00",
        "Pasos": "#,##0",
        "Distancia (m)": "#,##0",
        "Calorías\n(kcal)": "#,##0",
        "Minutos\nactivos": "0",
    }

    for row in ws.iter_rows(min_row=2):
        for header, fmt in fmt_map.items():
            idx = col_index.get(header)
            if idx is None:
                continue
            row[idx - 1].number_format = fmt
