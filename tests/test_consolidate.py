from __future__ import annotations

from datetime import date

import pandas as pd

from salud_tool.consolidate import consolidate_daily, drop_empty_days


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
