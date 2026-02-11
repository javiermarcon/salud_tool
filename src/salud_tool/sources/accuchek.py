"""Lectura de exportaciones JSON de Accu-Chek."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from dateutil import tz

from salud_tool.model import GlucoseReading
from salud_tool.sources.base import DataSource, SourcePaths

_LOCAL_TZ = tz.gettz("America/Argentina/Buenos_Aires")


@dataclass(frozen=True)
class AccuChekPaths(SourcePaths):
    """Paths for Accu-Chek JSON exports."""

    # root: folder containing accuchek_*.json


class AccuChekSource(DataSource):
    """Accu-Chek JSON reading source."""

    def validate(self) -> None:
        """Validate that the Accu-Chek export directory exists."""
        if not self._paths.root.exists():
            raise FileNotFoundError(str(self._paths.root))

    def newest_json(self) -> Path:
        """Return newest accuchek_*.json by mtime."""
        files = sorted(
            self._paths.root.glob("accuchek_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not files:
            raise FileNotFoundError(f"No accuchek_*.json in {self._paths.root}")
        return files[0]

    def load_readings(self, path: Path) -> list[GlucoseReading]:
        """Parse Accu-Chek JSON into typed readings.

        Args:
            path: Path to JSON file.

        Returns:
            List of glucose readings.

        Raises:
            ValueError: If JSON shape is invalid.
        """
        text = path.read_text(encoding="utf-8")
        raw = _extract_json_list(text)
        if not isinstance(raw, list):
            raise ValueError("Accu-Chek JSON must be a list")

        out: list[GlucoseReading] = []
        for item in raw:
            reading = _item_to_reading(item)
            if reading is not None:
                out.append(reading)
        out.sort(key=lambda r: r.timestamp)
        return out


def _parse_tag(item: dict[str, Any]) -> str | None:
    """Extrae y normaliza el tag de un ítem (vacío -> None)."""
    tag_val = item.get("tag")
    if tag_val is None:
        return None
    tag = str(tag_val).strip()
    return tag if tag else None


def _item_to_reading(item: Any) -> GlucoseReading | None:
    """Convierte un ítem dict en GlucoseReading; None si falta mg/dL o mmol/L."""
    if not isinstance(item, dict):
        return None
    mg_dl = item.get("mg/dL")
    mmol_l = item.get("mmol/L")
    if mg_dl is None or mmol_l is None:
        return None
    ts = _parse_timestamp(item.get("timestamp"), item.get("epoch"))
    tag = _parse_tag(item)
    return GlucoseReading(
        timestamp=ts,
        mg_dl=float(mg_dl),
        mmol_l=float(mmol_l),
        tag=tag,
    )


def _extract_json_list(text: str) -> Any:
    """Extract JSON array from text, tolerating leading non-JSON (e.g. log lines)."""
    start = text.find("[")
    if start >= 0:
        return json.loads(text[start:])
    return json.loads(text)


def _parse_timestamp(ts_str: Any, epoch: Any) -> datetime:
    """Parses the timestamps to get the date and time."""
    if isinstance(ts_str, str) and ts_str.strip():
        dt = datetime.strptime(ts_str, "%Y/%m/%d %H:%M")
        return dt.replace(tzinfo=_LOCAL_TZ)

    if epoch is not None:
        return datetime.fromtimestamp(int(epoch), tz=_LOCAL_TZ)

    raise ValueError("Missing timestamp and epoch")
