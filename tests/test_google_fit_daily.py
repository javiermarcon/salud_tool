"""Tests de normalización de CSV diario de Google Fit."""

from __future__ import annotations

import pandas as pd

from salud_tool.sources.google_fit import _normalize_daily_metrics


def test_fit_daily_normalizes_spanish_columns() -> None:
    """Normaliza columnas en castellano a columnas estándar."""
    df = pd.DataFrame(
        {
            "Fecha": ["2025-12-15", "2025-12-16"],
            "Pasos": [1000, 2000],
            "Distancia (m)": [500.0, 1200.0],
            "Calorías (kcal)": [80.5, 120.0],
            "Minutos activos": [10, 22],
        }
    )

    out = _normalize_daily_metrics(df)
    assert list(out.columns) == [
        "date",
        "steps",
        "distance_m",
        "calories_kcal",
        "active_minutes",
    ]
    assert out.loc[0, "steps"] == 1000
