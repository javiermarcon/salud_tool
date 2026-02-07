"""CLI para consolidar glucosa (Accu-Chek) + actividad (Google Fit) en Excel."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from dateutil import tz

from salud_tool.consolidate import (
    consolidate_daily,
    daily_glucose_summary,
    readings_to_frame,
)
from salud_tool.excel_writer import ExcelLayout, write_doctor_xlsx
from salud_tool.sources.accuchek import AccuChekPaths, AccuChekSource
from salud_tool.sources.google_fit import GoogleFitPaths, GoogleFitSource

_LOCAL_TZ = tz.gettz("America/Argentina/Buenos_Aires")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(
        description="Consolidación diaria: glucosa (Accu-Chek) + Google Fit."
    )
    parser.add_argument(
        "--base-dir",
        default=str(Path.home() / "proyectos" / "salud"),
        help="Directorio base (default: ~/proyectos/salud).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Rango de días hacia atrás (actualmente informativo).",
    )
    return parser.parse_args()


def main() -> int:
    """Run the consolidation CLI.

    Returns:
        Exit code (0 on success).
    """
    ns = parse_args()
    base = Path(ns.base_dir).expanduser().resolve()

    acc = AccuChekSource(AccuChekPaths(root=base / "glucosa" / "datos"))
    fit = GoogleFitSource(GoogleFitPaths(root=base / "fit" / "Takeout" / "Fit"))

    acc.validate()
    fit.validate()

    acc_file = acc.newest_json()
    readings = acc.load_readings(acc_file)

    glucose_events = readings_to_frame(readings)
    glucose_daily = daily_glucose_summary(glucose_events)

    fit_csvs = fit.daily_metrics_files()
    fit_daily = fit.load_daily(fit_csvs)

    consolidated = consolidate_daily(glucose_daily=glucose_daily, fit_daily=fit_daily)

    out_dir = base / "salidas"
    ts = datetime.now(tz=_LOCAL_TZ).strftime("%Y-%m-%d_%H-%M-%S")
    out_path = out_dir / f"salud_consolidada_diaria_{ts}.xlsx"

    write_doctor_xlsx(consolidated, out_path, ExcelLayout())

    print(f"OK: AccuChek file: {acc_file}")
    print(f"OK: Fit daily CSV files: {len(fit_csvs)}")
    print(f"OK: Output: {out_path}")
    return 0
