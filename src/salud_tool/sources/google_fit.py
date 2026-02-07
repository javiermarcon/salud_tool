"""Lectura de métricas diarias desde Google Fit Takeout."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast

import pandas as pd

from salud_tool.sources.base import DataSource, SourcePaths


@dataclass(frozen=True)
class GoogleFitPaths(SourcePaths):
    """Paths for Google Fit Takeout/Fit directory."""

    # root: .../Takeout/Fit


class GoogleFitSource(DataSource):
    """Google Fit Takeout reader (daily metrics)."""

    def validate(self) -> None:
        """Validate the path of the files."""
        if not self._paths.root.exists():
            raise FileNotFoundError(str(self._paths.root))

    def daily_metrics_files(self) -> list[Path]:
        """Return per-day CSV files for daily activity metrics."""
        metrics_dir = self._paths.root / "Métricas de actividad diaria"
        if not metrics_dir.exists():
            raise FileNotFoundError(str(metrics_dir))

        files = sorted(
            p
            for p in metrics_dir.glob("*.csv")
            if p.name.lower() != "métricas de actividad diaria.csv".lower()
        )
        if files:
            return files
        raise FileNotFoundError(str(metrics_dir))

    def load_daily(self, csv_paths: list[Path]) -> pd.DataFrame:
        """Load daily metrics from per-day CSVs.

        Returns DataFrame columns:
            date, steps, distance_m, calories_kcal, active_minutes
        """
        rows: list[dict[str, object]] = []
        for csv_path in csv_paths:
            file_date = _date_from_filename(csv_path)
            if not file_date:
                continue
            df = pd.read_csv(csv_path)
            row = _summarize_daily_file(df, file_date)
            if row:
                rows.append(row)

        if not rows:
            return pd.DataFrame(
                columns=[
                    "date",
                    "steps",
                    "distance_m",
                    "calories_kcal",
                    "active_minutes",
                ]
            )

        out = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        return out


def _find_col(columns: list[str], patterns: list[str]) -> str | None:
    for pat in patterns:
        rx = re.compile(pat, re.IGNORECASE)
        for c in columns:
            if rx.search(c):
                return c
    return None


def _summarize_daily_file(
    df: pd.DataFrame, file_date: date
) -> dict[str, object] | None:
    if df.empty:
        return None

    df = df.rename(columns={c: c.strip() for c in df.columns})
    cols = list(df.columns)

    steps_col = _find_col(cols, [r"\bpasos\b", r"\bstep"])
    dist_col = _find_col(cols, [r"\bdistancia\b", r"\bdistance"])
    cal_col = _find_col(cols, [r"\bcalor", r"\bcalorie"])
    act_col = _find_col(cols, [r"minutos activos", r"active minutes", r"\bactive_min"])

    def sum_or_na(series_name: str | None) -> float | int | None:
        if not series_name:
            return None
        result = pd.to_numeric(df[series_name], errors="coerce").sum(min_count=1)
        if pd.isna(result):
            return None
        if hasattr(result, "item"):
            return cast(float | int, result.item())
        return cast(float | int, result)

    return {
        "date": file_date,
        "steps": sum_or_na(steps_col),
        "distance_m": sum_or_na(dist_col),
        "calories_kcal": sum_or_na(cal_col),
        "active_minutes": sum_or_na(act_col),
    }


def _date_from_filename(path: Path) -> date | None:
    match = re.match(r"(\d{4}-\d{2}-\d{2})", path.stem)
    if not match:
        return None
    parsed = pd.to_datetime(match.group(1), errors="coerce")
    if pd.isna(parsed):
        return None
    return cast(date, parsed.date())
