"""Tests for Google Fit daily metrics reader."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from salud_tool.sources.google_fit import (
    GoogleFitPaths,
    GoogleFitSource,
    _date_from_filename,
    _find_col,
    _summarize_daily_file,
)


def _write_csv(path: Path, data: dict[str, list[object]]) -> None:
    pd.DataFrame(data).to_csv(path, index=False)


def test_find_col_matches_spanish_and_english() -> None:
    cols = ["Fecha", "Pasos", "Distance (m)", "Calorías", "Minutos activos"]
    assert _find_col(cols, [r"\bpasos\b", r"\bstep"]) == "Pasos"
    assert _find_col(cols, [r"\bdistance\b"]) == "Distance (m)"
    assert _find_col(cols, [r"minutos activos"]) == "Minutos activos"
    assert _find_col(cols, [r"\bunknown\b"]) is None


def test_date_from_filename_valid_and_invalid() -> None:
    assert _date_from_filename(Path("2025-12-15.csv")) == date(2025, 12, 15)
    assert _date_from_filename(Path("2025-13-99.csv")) is None
    assert _date_from_filename(Path("no-date.csv")) is None


def test_summarize_daily_file_empty_df() -> None:
    df = pd.DataFrame()
    assert _summarize_daily_file(df, date(2025, 12, 15)) is None


def test_summarize_daily_file_happy_path_and_coercion() -> None:
    df = pd.DataFrame(
        {
            " Pasos ": ["1000", "2000"],
            "Distancia (m)": ["500.0", "1200.0"],
            "Calorías (kcal)": ["80.5", "bad"],
            "Minutos activos": [10, None],
        }
    )
    out = _summarize_daily_file(df, date(2025, 12, 15))
    assert out is not None
    assert out["date"] == date(2025, 12, 15)
    assert out["steps"] == 3000
    assert out["distance_m"] == 1700.0
    assert out["calories_kcal"] == 80.5
    assert out["active_minutes"] == 10


def test_summarize_daily_file_missing_columns() -> None:
    df = pd.DataFrame({"Other": [1, 2]})
    out = _summarize_daily_file(df, date(2025, 12, 15))
    assert out is not None
    assert out["steps"] is None
    assert out["distance_m"] is None
    assert out["calories_kcal"] is None
    assert out["active_minutes"] is None


def test_validate_and_daily_metrics_files_errors(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"
    source = GoogleFitSource(GoogleFitPaths(root=missing_root))
    with pytest.raises(FileNotFoundError):
        source.validate()

    root = tmp_path / "Fit"
    root.mkdir()
    source = GoogleFitSource(GoogleFitPaths(root=root))
    with pytest.raises(FileNotFoundError):
        source.daily_metrics_files()

    metrics = root / "Métricas de actividad diaria"
    metrics.mkdir()
    with pytest.raises(FileNotFoundError):
        source.daily_metrics_files()


def test_daily_metrics_files_happy_path_excludes_summary(tmp_path: Path) -> None:
    root = tmp_path / "Fit"
    metrics = root / "Métricas de actividad diaria"
    metrics.mkdir(parents=True)
    day_a = metrics / "2025-12-15.csv"
    day_b = metrics / "2025-12-16.csv"
    summary = metrics / "Métricas de actividad diaria.csv"
    for p in (day_b, day_a, summary):
        _write_csv(p, {"Pasos": [1]})

    source = GoogleFitSource(GoogleFitPaths(root=root))
    files = source.daily_metrics_files()
    assert files == [day_a, day_b]


def test_load_daily_skips_bad_filenames_and_empty() -> None:
    source = GoogleFitSource(GoogleFitPaths(root=Path(".")))
    out = source.load_daily([Path("no-date.csv")])
    assert list(out.columns) == [
        "date",
        "steps",
        "distance_m",
        "calories_kcal",
        "active_minutes",
    ]
    assert out.empty


def test_load_daily_happy_path_and_sorting(tmp_path: Path) -> None:
    day_a = tmp_path / "2025-12-15.csv"
    day_b = tmp_path / "2025-12-16.csv"
    _write_csv(
        day_a,
        {
            "Pasos": [1000],
            "Distancia (m)": [500.0],
            "Calorías (kcal)": [80.5],
            "Minutos activos": [10],
        },
    )
    _write_csv(
        day_b,
        {
            "Pasos": [2000],
            "Distancia (m)": [1200.0],
            "Calorías (kcal)": [120.0],
            "Minutos activos": [22],
        },
    )

    source = GoogleFitSource(GoogleFitPaths(root=Path(".")))
    out = source.load_daily([day_b, day_a])
    assert list(out["date"]) == [date(2025, 12, 15), date(2025, 12, 16)]
    assert list(out["steps"]) == [1000, 2000]
