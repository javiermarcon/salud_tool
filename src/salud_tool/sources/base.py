"""Clases base para fuentes de datos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourcePaths:
    """Container for source directories."""

    root: Path


class DataSource(ABC):
    """Abstract data source."""

    def __init__(self, paths: SourcePaths) -> None:
        """Create a data source.

        Args:
            paths: Source paths configuration.
        """
        self._paths = paths

    @abstractmethod
    def validate(self) -> None:
        """Validate that required folders/files exist.

        Raises:
            FileNotFoundError: If required files are missing.
        """
