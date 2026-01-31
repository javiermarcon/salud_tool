"""Modelos tipados para eventos de glucosa y actividad diaria."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class GlucoseReading:
    """One glucose measurement event (timestamped)."""

    timestamp: datetime
    mg_dl: float
    mmol_l: float


@dataclass(frozen=True)
class DailyActivity:
    """Daily activity metrics (date-based)."""

    day: date
    steps: float | None = None
    distance_m: float | None = None
    calories_kcal: float | None = None
    active_minutes: float | None = None
