"""Persistencia SQLite para configuracion, corridas y datos procesados."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS process_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    acc_root TEXT NOT NULL,
    fit_root TEXT NOT NULL,
    acc_file TEXT,
    fit_files_count INTEGER NOT NULL,
    rows_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS processed_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    row_hash TEXT,
    date TEXT,
    datetime TEXT,
    glucose_mg_dl REAL,
    tag TEXT,
    steps REAL,
    distance_m REAL,
    calories_kcal REAL,
    active_minutes REAL,
    FOREIGN KEY(run_id) REFERENCES process_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_processed_rows_row_hash
ON processed_rows(row_hash);
"""


@dataclass(frozen=True)
class AppConfig:
    """Configuracion persistida de la app."""

    acc_root: str
    fit_root: str
    export_dir: str
    selected_fields: list[str]


class SQLiteStore:
    """Repositorio SQLite para la app."""

    def __init__(self, db_path: Path) -> None:
        """Create store and ensure schema exists."""
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            self._migrate(conn)
            conn.commit()

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Apply lightweight schema/data migrations."""
        cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(processed_rows)")
        }
        if "row_hash" not in cols:
            conn.execute("ALTER TABLE processed_rows ADD COLUMN row_hash TEXT")

        rows = conn.execute(
            """
            SELECT
                id, date, datetime, glucose_mg_dl, tag, steps,
                distance_m, calories_kcal, active_minutes
            FROM processed_rows
            WHERE row_hash IS NULL
            """
        ).fetchall()
        for row in rows:
            values = (
                row["date"],
                row["datetime"],
                row["glucose_mg_dl"],
                row["tag"],
                row["steps"],
                row["distance_m"],
                row["calories_kcal"],
                row["active_minutes"],
            )
            conn.execute(
                "UPDATE processed_rows SET row_hash = ? WHERE id = ?",
                (_row_hash(values), row["id"]),
            )

        # Remove historical duplicates before enforcing uniqueness.
        conn.execute(
            """
            DELETE FROM processed_rows
            WHERE id NOT IN (
                SELECT MIN(id) FROM processed_rows
                GROUP BY row_hash
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_processed_rows_row_hash_unique
            ON processed_rows(row_hash)
            """
        )

    def load_config(self) -> AppConfig:
        """Devuelve configuracion guardada o defaults."""
        defaults = {
            "acc_root": "",
            "fit_root": "",
            "export_dir": "",
            "selected_fields": json.dumps(_default_fields()),
        }
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM app_config").fetchall()
        values = {row["key"]: row["value"] for row in rows}
        merged = {**defaults, **values}
        selected_fields = _parse_json_list(merged["selected_fields"])
        return AppConfig(
            acc_root=merged["acc_root"],
            fit_root=merged["fit_root"],
            export_dir=merged["export_dir"],
            selected_fields=selected_fields,
        )

    def save_config(self, config: AppConfig) -> None:
        """Guarda la configuracion en tabla key/value."""
        payload = {
            "acc_root": config.acc_root,
            "fit_root": config.fit_root,
            "export_dir": config.export_dir,
            "selected_fields": json.dumps(config.selected_fields),
        }
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO app_config(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                payload.items(),
            )
            conn.commit()

    def save_processed_run(
        self,
        consolidated: pd.DataFrame,
        *,
        acc_root: str,
        fit_root: str,
        acc_file: str | None,
        fit_files_count: int,
    ) -> int | None:
        """Guarda corrida y filas nuevas. Devuelve run_id o None si no hay nuevas."""
        created_at = datetime.now().isoformat(timespec="seconds")
        rows = _rows_from_df(consolidated)
        with self._connect() as conn:
            existing_hashes = _existing_hashes(conn, [row[0] for row in rows])
            new_rows = [row for row in rows if row[0] not in existing_hashes]
            if not new_rows:
                return None

            cur = conn.execute(
                """
                INSERT INTO process_runs(
                    created_at, acc_root, fit_root, acc_file,
                    fit_files_count, rows_count
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    acc_root,
                    fit_root,
                    acc_file,
                    fit_files_count,
                    len(new_rows),
                ),
            )
            run_id = int(cur.lastrowid)
            if new_rows:
                conn.executemany(
                    """
                    INSERT INTO processed_rows(
                        run_id, row_hash, date, datetime, glucose_mg_dl, tag, steps,
                        distance_m, calories_kcal, active_minutes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [(run_id, *row) for row in new_rows],
                )
            conn.commit()
        return run_id

    def load_run_dataframe(self, run_id: int) -> pd.DataFrame:
        """Carga una corrida como DataFrame."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    date, datetime, glucose_mg_dl, tag, steps,
                    distance_m, calories_kcal, active_minutes
                FROM processed_rows
                WHERE run_id = ?
                ORDER BY datetime
                """,
                (run_id,),
            ).fetchall()

        records = [dict(row) for row in rows]
        out = pd.DataFrame(records)
        if out.empty:
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
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.date
        out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")
        return out

    def latest_run_id(self) -> int | None:
        """Obtiene id de la corrida mas reciente."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM process_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return int(row["id"])


def _default_fields() -> list[str]:
    return [
        "date",
        "datetime",
        "glucose_mg_dl",
        "tag",
        "steps",
        "distance_m",
        "calories_kcal",
        "active_minutes",
    ]


def _parse_json_list(raw: str) -> list[str]:
    try:
        parsed: Any = json.loads(raw)
    except json.JSONDecodeError:
        return _default_fields()
    if not isinstance(parsed, list):
        return _default_fields()
    out = [str(item) for item in parsed]
    return out or _default_fields()


def _safe_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if pd.isna(value):
        return None
    return value


def _rows_from_df(df: pd.DataFrame) -> list[tuple[object, ...]]:
    if df.empty:
        return []
    out: list[tuple[object, ...]] = []
    for _, row in df.iterrows():
        date_value = _safe_value(row.get("date"))
        datetime_value = _safe_value(row.get("datetime"))
        normalized = (
            date_value.isoformat() if hasattr(date_value, "isoformat") else date_value,
            datetime_value.isoformat()
            if hasattr(datetime_value, "isoformat")
            else datetime_value,
            _safe_value(row.get("glucose_mg_dl")),
            _safe_value(row.get("tag")),
            _safe_value(row.get("steps")),
            _safe_value(row.get("distance_m")),
            _safe_value(row.get("calories_kcal")),
            _safe_value(row.get("active_minutes")),
        )
        out.append((_row_hash(normalized), *normalized))
    return out


def _row_hash(values: tuple[object, ...]) -> str:
    payload = json.dumps(values, ensure_ascii=True, sort_keys=False, default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _existing_hashes(conn: sqlite3.Connection, hashes: list[object]) -> set[str]:
    valid_hashes = [h for h in hashes if isinstance(h, str)]
    if not valid_hashes:
        return set()
    placeholders = ",".join("?" for _ in valid_hashes)
    rows = conn.execute(
        f"SELECT row_hash FROM processed_rows WHERE row_hash IN ({placeholders})",
        tuple(valid_hashes),
    ).fetchall()
    return {str(row["row_hash"]) for row in rows if row["row_hash"]}
