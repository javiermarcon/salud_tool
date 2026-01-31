"""Lectura de métricas diarias desde Google Fit Takeout."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

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

    def daily_metrics_csv(self) -> Path:
        """Return the consolidated 'Métricas de actividad diaria.csv' if present."""
        metrics_dir = self._paths.root / "Métricas de actividad diaria"
        consolidated = metrics_dir / "Métricas de actividad diaria.csv"
        if consolidated.exists():
            return consolidated
        raise FileNotFoundError(str(consolidated))

    def load_daily(self, csv_path: Path) -> pd.DataFrame:
        """Load daily metrics to a normalized DataFrame.

        Returns DataFrame columns:
            date, steps, distance_m, calories_kcal, active_minutes
        """
        df = pd.read_csv(csv_path)
        norm = _normalize_daily_metrics(df)
        return norm


def _find_col(columns: list[str], patterns: list[str]) -> str | None:
    for pat in patterns:
        rx = re.compile(pat, re.IGNORECASE)
        for c in columns:
            if rx.search(c):
                return c
    return None


def _normalize_daily_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=["date", "steps", "distance_m", "calories_kcal", "active_minutes"]
        )

    df = df.rename(columns={c: c.strip() for c in df.columns})
    cols = list(df.columns)

    date_col = _find_col(cols, [r"\b(fecha|date)\b"])
    if not date_col:
        return pd.DataFrame(
            columns=["date", "steps", "distance_m", "calories_kcal", "active_minutes"]
        )

    steps_col = _find_col(cols, [r"\bpasos\b", r"\bstep"])
    dist_col = _find_col(cols, [r"\bdistancia\b", r"\bdistance"])
    cal_col = _find_col(cols, [r"\bcalor", r"\bcalorie"])
    act_col = _find_col(cols, [r"minutos activos", r"active minutes", r"\bactive_min"])

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.date

    def num(series_name: str | None) -> pd.Series:
        if not series_name:
            return pd.Series([pd.NA] * len(df))
        return pd.to_numeric(df[series_name], errors="coerce")

    out["steps"] = num(steps_col)
    out["distance_m"] = num(dist_col)
    out["calories_kcal"] = num(cal_col)
    out["active_minutes"] = num(act_col)

    out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return out
