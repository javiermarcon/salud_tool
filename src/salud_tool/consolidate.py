"""Funciones de consolidación diaria (calendario + merges + filtros)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import cast

import pandas as pd

from salud_tool.model import GlucoseReading


@dataclass(frozen=True)
class ConsolidationConfig:
    """Configuration for daily consolidation."""

    days_back: int


def readings_to_frame(readings: Sequence[GlucoseReading]) -> pd.DataFrame:
    """Convert glucose readings to DataFrame with date/time and optional tag."""
    rows = [
        {
            "datetime": r.timestamp,
            "date": r.timestamp.date(),
            "time": r.timestamp.time().replace(second=0, microsecond=0),
            "glucose_mg_dl": r.mg_dl,
            "glucose_mmol_l": r.mmol_l,
            "tag": r.tag,
        }
        for r in readings
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("datetime").reset_index(drop=True)


def daily_glucose_summary(glucose_events: pd.DataFrame) -> pd.DataFrame:
    """Aggregate glucose by day (count/min/max/avg)."""
    if glucose_events.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "glucose_count",
                "glucose_min",
                "glucose_max",
                "glucose_avg",
                "mmol_avg",
            ]
        )
    g = glucose_events.groupby("date", as_index=False).agg(
        glucose_count=("glucose_mg_dl", "count"),
        glucose_min=("glucose_mg_dl", "min"),
        glucose_max=("glucose_mg_dl", "max"),
        glucose_avg=("glucose_mg_dl", "mean"),
        mmol_avg=("glucose_mmol_l", "mean"),
    )
    g["glucose_avg"] = g["glucose_avg"].round(2)
    g["mmol_avg"] = g["mmol_avg"].round(2)
    return g.sort_values("date").reset_index(drop=True)


def consolidate_readings(
    glucose_events: pd.DataFrame,
    fit_daily: pd.DataFrame,
) -> pd.DataFrame:
    """One row per glucose measurement, with fitness merged by date.

    Args:
        glucose_events: One row per reading (datetime, date, glucose_mg_dl, ...).
        fit_daily: Daily metrics (date, steps, distance_m, ...).

    Returns:
        DataFrame with one row per reading: date, datetime, glucose_mg_dl,
        steps, distance_m, calories_kcal, active_minutes.
    """
    if glucose_events.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "datetime",
                "glucose_mg_dl",
                "tag",
                "steps",
                "distance_m",
                "calories_kcal",
                "active_minutes",
            ]
        )
    out = glucose_events.merge(fit_daily, on="date", how="left")
    cols = [
        "date",
        "datetime",
        "glucose_mg_dl",
        "tag",
        "steps",
        "distance_m",
        "calories_kcal",
        "active_minutes",
    ]
    out = out[[c for c in cols if c in out.columns]]
    return out.sort_values("datetime").reset_index(drop=True)


def build_calendar(min_day: date, max_day: date) -> pd.DataFrame:
    """Build inclusive day calendar DataFrame."""
    days = pd.date_range(start=min_day, end=max_day, freq="D")
    return pd.DataFrame({"date": days.date})


def consolidate_daily(
    glucose_daily: pd.DataFrame,
    fit_daily: pd.DataFrame,
) -> pd.DataFrame:
    """Full outer daily consolidation.

    Result includes all dates from either source.
    """
    if glucose_daily.empty and fit_daily.empty:
        return pd.DataFrame()

    min_day = _min_date(glucose_daily, fit_daily)
    max_day = _max_date(glucose_daily, fit_daily)
    cal = build_calendar(min_day=min_day, max_day=max_day)

    out = cal.merge(glucose_daily, on="date", how="left").merge(
        fit_daily, on="date", how="left"
    )
    out = out.sort_values("date").reset_index(drop=True)
    return drop_empty_days(out)


def _min_date(glucose_daily: pd.DataFrame, fit_daily: pd.DataFrame) -> date:
    mins = []
    if not glucose_daily.empty:
        mins.append(cast(date, min(glucose_daily["date"])))
    if not fit_daily.empty:
        mins.append(cast(date, min(fit_daily["date"])))
    return min(mins)


def _max_date(glucose_daily: pd.DataFrame, fit_daily: pd.DataFrame) -> date:
    maxs = []
    if not glucose_daily.empty:
        maxs.append(cast(date, max(glucose_daily["date"])))
    if not fit_daily.empty:
        maxs.append(cast(date, max(fit_daily["date"])))
    return max(maxs)


def drop_empty_days(df: pd.DataFrame) -> pd.DataFrame:
    """Drop days where every metric column is null/NA.

    Args:
        df: Consolidated daily DataFrame.

    Returns:
        DataFrame without fully-empty days.
    """
    if df.empty:
        return df

    candidate_cols = [
        "glucose_count",
        "glucose_min",
        "glucose_max",
        "glucose_avg",
        "mmol_avg",
        "steps",
        "distance_m",
        "calories_kcal",
        "active_minutes",
    ]
    existing = [c for c in candidate_cols if c in df.columns]
    if not existing:
        return df

    mask = df[existing].notna().any(axis=1)
    return df.loc[mask].reset_index(drop=True)
