from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from salud_tool.consolidate import (
    _max_date,
    _min_date,
    build_calendar,
    consolidate_daily,
    daily_glucose_summary,
    drop_empty_days,
    readings_to_frame,
)
from salud_tool.model import GlucoseReading


def test_readings_to_frame_empty() -> None:
    df = readings_to_frame([])
    assert df.empty


def test_readings_to_frame_orders_and_truncates_time() -> None:
    readings = [
        GlucoseReading(
            timestamp=datetime(2025, 12, 16, 8, 30, 45, 123),
            mg_dl=110.0,
            mmol_l=6.1,
        ),
        GlucoseReading(
            timestamp=datetime(2025, 12, 15, 7, 15, 59, 999),
            mg_dl=100.0,
            mmol_l=5.5,
        ),
    ]
    df = readings_to_frame(readings)
    assert list(df["date"]) == [date(2025, 12, 15), date(2025, 12, 16)]
    assert list(df["time"])[0].second == 0
    assert list(df["time"])[0].microsecond == 0


def test_daily_glucose_summary_empty() -> None:
    out = daily_glucose_summary(pd.DataFrame())
    assert list(out.columns) == [
        "date",
        "glucose_count",
        "glucose_min",
        "glucose_max",
        "glucose_avg",
        "mmol_avg",
    ]
    assert out.empty


def test_daily_glucose_summary_rounding() -> None:
    df = pd.DataFrame(
        {
            "date": [date(2025, 12, 15), date(2025, 12, 15)],
            "glucose_mg_dl": [100.123, 110.987],
            "glucose_mmol_l": [5.567, 6.789],
        }
    )
    out = daily_glucose_summary(df)
    assert out.loc[0, "glucose_avg"] == 105.56
    assert out.loc[0, "mmol_avg"] == 6.18


def test_build_calendar_inclusive() -> None:
    cal = build_calendar(date(2025, 12, 15), date(2025, 12, 17))
    assert list(cal["date"]) == [
        date(2025, 12, 15),
        date(2025, 12, 16),
        date(2025, 12, 17),
    ]


def test_min_max_date_with_one_empty() -> None:
    glucose = pd.DataFrame({"date": [date(2025, 12, 15)]})
    fit = pd.DataFrame({"date": [date(2025, 12, 17)]})
    assert _min_date(glucose_daily=glucose, fit_daily=pd.DataFrame()) == date(
        2025, 12, 15
    )
    assert _max_date(glucose_daily=pd.DataFrame(), fit_daily=fit) == date(2025, 12, 17)


def test_consolidate_daily_empty_returns_empty_df() -> None:
    out = consolidate_daily(pd.DataFrame(), pd.DataFrame())
    assert out.empty


def test_consolidate_includes_fit_only_days() -> None:
    glucose = pd.DataFrame(
        {
            "date": [date(2025, 12, 15)],
            "glucose_count": [1],
            "glucose_min": [100.0],
            "glucose_max": [100.0],
            "glucose_avg": [100.0],
            "mmol_avg": [5.55],
        }
    )
    fit = pd.DataFrame(
        {
            "date": [date(2025, 12, 15), date(2025, 12, 16)],
            "steps": [1000, 2000],
            "distance_m": [500.0, 1200.0],
            "calories_kcal": [80.0, 120.0],
            "active_minutes": [10.0, 22.0],
        }
    )

    out = consolidate_daily(glucose_daily=glucose, fit_daily=fit)
    assert len(out) == 2
    assert out.loc[1, "date"] == date(2025, 12, 16)
    assert out.loc[1, "steps"] == 2000


def test_consolidate_drops_empty_calendar_days() -> None:
    glucose = pd.DataFrame(
        {
            "date": [date(2025, 12, 15)],
            "glucose_count": [1],
            "glucose_min": [100.0],
            "glucose_max": [100.0],
            "glucose_avg": [100.0],
            "mmol_avg": [5.55],
        }
    )
    fit = pd.DataFrame(
        {
            "date": [date(2025, 12, 17)],
            "steps": [2000],
            "distance_m": [1200.0],
            "calories_kcal": [120.0],
            "active_minutes": [22.0],
        }
    )
    out = consolidate_daily(glucose_daily=glucose, fit_daily=fit)
    assert list(out["date"]) == [date(2025, 12, 15), date(2025, 12, 17)]


def test_drop_empty_days_removes_all_nan_rows() -> None:
    df = pd.DataFrame(
        {
            "date": [date(2025, 12, 15), date(2025, 12, 16)],
            "steps": [1000, pd.NA],
            "glucose_avg": [pd.NA, pd.NA],
        }
    )
    out = drop_empty_days(df)
    assert len(out) == 1
    assert out.loc[0, "date"] == date(2025, 12, 15)


def test_drop_empty_days_empty_and_no_candidate_cols() -> None:
    empty = pd.DataFrame()
    assert drop_empty_days(empty).empty

    df = pd.DataFrame({"date": [date(2025, 12, 15)], "other": [1]})
    out = drop_empty_days(df)
    assert out.equals(df)
