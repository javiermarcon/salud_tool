"""Punto de entrada de la app Kivy."""

from __future__ import annotations

from salud_tool.app import run_app


def main() -> int:
    """Run app entrypoint."""
    try:
        return run_app()
    except ImportError as exc:
        print(f"No se pudo iniciar Kivy: {exc}")
        print("Instala dependencias de GUI: pip install kivy")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
