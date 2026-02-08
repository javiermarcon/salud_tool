"""Tests for CLI entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

from salud_tool import cli


def test_parse_args_custom_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["prog", "--base-dir", "/tmp/base", "--days", "10"])
    ns = cli.parse_args()
    assert ns.base_dir == "/tmp/base"
    assert ns.days == 10


def test_main_happy_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    @dataclass(frozen=True)
    class _Args:
        base_dir: str
        days: int

    class _AccuChekSource:
        def __init__(self, paths: Any) -> None:
            self.paths = paths

        def validate(self) -> None:
            return None

        def newest_json(self) -> Path:
            return Path("acc.json")

        def load_readings(self, _: Path) -> list[str]:
            return ["r1"]

    class _GoogleFitSource:
        def __init__(self, paths: Any) -> None:
            self.paths = paths

        def validate(self) -> None:
            return None

        def daily_metrics_files(self) -> list[Path]:
            return [Path("2025-12-15.csv"), Path("2025-12-16.csv")]

        def load_daily(self, _: list[Path]) -> pd.DataFrame:
            return pd.DataFrame({"date": [datetime(2025, 12, 15).date()]})

    def _readings_to_frame(_: list[str]) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": [datetime(2025, 12, 15).date()],
                "datetime": [pd.Timestamp("2025-12-15 08:00")],
                "glucose_mg_dl": [100.0],
            }
        )

    def _consolidate_readings(
        glucose_events: pd.DataFrame, fit_daily: pd.DataFrame
    ) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": [datetime(2025, 12, 15).date()],
                "datetime": [pd.Timestamp("2025-12-15 08:00")],
                "glucose_mg_dl": [100.0],
                "steps": [1000],
            }
        )

    captured: dict[str, object] = {}

    def _write_doctor_xlsx(df: pd.DataFrame, out_path: Path, _: Any) -> None:
        captured["df"] = df
        captured["out_path"] = out_path

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz: Any | None = None) -> _FixedDatetime:
            return cls(2025, 12, 31, 23, 59, 1, tzinfo=tz)

    monkeypatch.setattr(cli, "parse_args", lambda: _Args(str(tmp_path), 7))
    monkeypatch.setattr(cli, "AccuChekSource", _AccuChekSource)
    monkeypatch.setattr(cli, "GoogleFitSource", _GoogleFitSource)
    monkeypatch.setattr(cli, "readings_to_frame", _readings_to_frame)
    monkeypatch.setattr(cli, "consolidate_readings", _consolidate_readings)
    monkeypatch.setattr(cli, "write_doctor_xlsx", _write_doctor_xlsx)
    monkeypatch.setattr(cli, "datetime", _FixedDatetime)

    code = cli.main()
    assert code == 0
    df = cast(pd.DataFrame, captured["df"])
    out_path = cast(Path, captured["out_path"])
    assert df.shape[0] == 1
    assert out_path.name.startswith("salud_consolidada_diaria_")


def test_main_propagates_validation_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    @dataclass(frozen=True)
    class _Args:
        base_dir: str
        days: int

    class _AccuChekSource:
        def __init__(self, paths: Any) -> None:
            self.paths = paths

        def validate(self) -> None:
            raise FileNotFoundError("missing")

    monkeypatch.setattr(cli, "parse_args", lambda: _Args(str(tmp_path), 7))
    monkeypatch.setattr(cli, "AccuChekSource", _AccuChekSource)

    class _GoogleFitSource:
        def __init__(self, paths: Any) -> None:
            self.paths = paths

        def validate(self) -> None:
            return None

    monkeypatch.setattr(cli, "GoogleFitSource", _GoogleFitSource)

    with pytest.raises(FileNotFoundError):
        cli.main()
