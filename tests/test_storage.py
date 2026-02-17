from __future__ import annotations

from pathlib import Path

import pandas as pd

from salud_tool.storage import AppConfig, SQLiteStore


def test_store_config_and_processed_rows(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "app.sqlite3")
    config = AppConfig(
        acc_root="/data/acc",
        fit_root="/data/fit",
        export_dir="/data/out",
        selected_fields=["date", "glucose_mg_dl"],
    )
    store.save_config(config)
    loaded = store.load_config()
    assert loaded.acc_root == "/data/acc"
    assert loaded.fit_root == "/data/fit"
    assert loaded.selected_fields == ["date", "glucose_mg_dl"]

    df = pd.DataFrame(
        {
            "date": [pd.to_datetime("2025-01-02").date()],
            "datetime": [pd.Timestamp("2025-01-02 08:00:00")],
            "glucose_mg_dl": [123.0],
            "tag": ["ayuno"],
            "steps": [2000.0],
            "distance_m": [1200.0],
            "calories_kcal": [140.0],
            "active_minutes": [21.0],
        }
    )

    run_id = store.save_processed_run(
        df,
        acc_root=config.acc_root,
        fit_root=config.fit_root,
        acc_file="/data/acc/accuchek_1.json",
        fit_files_count=4,
    )
    assert run_id is not None
    assert run_id > 0
    assert store.latest_run_id() == run_id

    stored_df = store.load_run_dataframe(run_id)
    assert len(stored_df) == 1
    assert stored_df.iloc[0]["glucose_mg_dl"] == 123.0
    assert stored_df.iloc[0]["steps"] == 2000.0


def test_store_skips_duplicate_processed_rows(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "app.sqlite3")
    df = pd.DataFrame(
        {
            "date": [pd.to_datetime("2025-01-02").date()],
            "datetime": [pd.Timestamp("2025-01-02 08:00:00")],
            "glucose_mg_dl": [123.0],
            "tag": ["ayuno"],
            "steps": [2000.0],
            "distance_m": [1200.0],
            "calories_kcal": [140.0],
            "active_minutes": [21.0],
        }
    )

    first_run = store.save_processed_run(
        df,
        acc_root="/a",
        fit_root="/b",
        acc_file="/a/file.json",
        fit_files_count=1,
    )
    second_run = store.save_processed_run(
        df,
        acc_root="/a",
        fit_root="/b",
        acc_file="/a/file.json",
        fit_files_count=1,
    )

    assert first_run is not None
    assert second_run is None
