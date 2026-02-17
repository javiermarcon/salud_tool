"""App Kivy con configuracion por pestañas y persistencia SQLite."""

from __future__ import annotations

import traceback
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from salud_tool.consolidate import consolidate_readings, readings_to_frame
from salud_tool.excel_writer import ExcelLayout, write_doctor_xlsx
from salud_tool.sources.accuchek import AccuChekPaths, AccuChekSource
from salud_tool.sources.google_fit import GoogleFitPaths, GoogleFitSource
from salud_tool.storage import AppConfig, SQLiteStore

BASE_FIELDS = ["date", "datetime"]
ACCU_FIELDS = ["glucose_mg_dl", "tag"]
FIT_FIELDS = ["steps", "distance_m", "calories_kcal", "active_minutes"]


def run_app() -> int:
    """Lanza la app Kivy."""
    from kivy.app import App
    from kivy.core.window import Window
    from kivy.resources import resource_find
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.checkbox import CheckBox
    from kivy.uix.filechooser import FileChooserListView
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
    from kivy.uix.popup import Popup
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
    from kivy.uix.textinput import TextInput

    class SaludToolApp(App):
        """Main Kivy app."""

        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            self.store = SQLiteStore(Path.cwd() / "salud_tool.sqlite3")
            self.app_config = self.store.load_config()
            self.current_df = pd.DataFrame()
            self.current_run_id: int | None = None
            self.preview: TextInput | None = None
            self.status: Label | None = None
            self._preview_font = resource_find("data/fonts/RobotoMono-Regular.ttf")

        def build(self) -> BoxLayout:
            Window.bind(on_key_down=self._on_key_down)

            root = BoxLayout(orientation="vertical", spacing=8, padding=10)
            root.add_widget(
                Label(
                    text=(
                        "Salud Tool: Configuracion por pestañas, luego Procesar y "
                        "Exportar."
                    ),
                    size_hint_y=None,
                    height=36,
                )
            )

            actions = BoxLayout(
                orientation="horizontal",
                spacing=8,
                size_hint_y=None,
                height=40,
            )
            settings_btn = Button(text="Configuracion")
            process_btn = Button(text="Procesar y guardar")
            export_btn = Button(text="Exportar Excel")
            exit_btn = Button(text="Salir")
            settings_btn.bind(on_press=self._open_config_popup)
            process_btn.bind(on_press=self._on_process)
            export_btn.bind(on_press=self._on_export)
            exit_btn.bind(on_press=lambda *_args: self.stop())
            actions.add_widget(settings_btn)
            actions.add_widget(process_btn)
            actions.add_widget(export_btn)
            actions.add_widget(exit_btn)
            root.add_widget(actions)

            self.status = Label(text="Sin procesar", size_hint_y=None, height=30)
            root.add_widget(self.status)

            self.preview = TextInput(
                readonly=True,
                text="",
                multiline=True,
                do_wrap=False,
            )
            if self._preview_font:
                self.preview.font_name = self._preview_font
            root.add_widget(self.preview)

            self._load_latest_run()
            return root

        def _on_key_down(
            self,
            _window: object,
            keycode: int,
            _scancode: int,
            _text: str,
            _modifiers: list[str],
        ) -> bool:
            # Esc: salir de fullscreen o cerrar app.
            if keycode != 27:
                return False
            if Window.fullscreen:
                Window.fullscreen = False
            else:
                self.stop()
            return True

        def _open_config_popup(self, _: object) -> None:
            panel = TabbedPanel(do_default_tab=False)
            path_inputs: dict[str, TextInput] = {}
            field_checks: dict[str, CheckBox] = {}

            def make_path_row(label: str, key: str, initial: str) -> BoxLayout:
                row = BoxLayout(orientation="horizontal", size_hint_y=None, height=36)
                row.add_widget(Label(text=label, size_hint_x=0.25))
                inp = TextInput(text=initial, multiline=False)
                row.add_widget(inp)
                browse_btn = Button(text="Browse", size_hint_x=0.2)
                browse_btn.bind(on_press=lambda *_args: self._open_path_chooser(inp))
                row.add_widget(browse_btn)
                path_inputs[key] = inp
                return row

            def make_fields_grid(fields: list[str]) -> ScrollView:
                grid = GridLayout(cols=1, spacing=4, size_hint_y=None)
                grid.bind(minimum_height=grid.setter("height"))
                for field in fields:
                    row = BoxLayout(
                        orientation="horizontal",
                        size_hint_y=None,
                        height=30,
                    )
                    chk = CheckBox(active=field in self.app_config.selected_fields)
                    field_checks[field] = chk
                    row.add_widget(chk)
                    row.add_widget(Label(text=field))
                    grid.add_widget(row)
                scroll = ScrollView()
                scroll.add_widget(grid)
                return scroll

            general = TabbedPanelItem(text="General")
            general_box = BoxLayout(orientation="vertical", spacing=8, padding=8)
            general_box.add_widget(
                make_path_row(
                    "Path salida",
                    "export_dir",
                    self.app_config.export_dir,
                )
            )
            general.add_widget(general_box)
            panel.add_widget(general)

            accu = TabbedPanelItem(text="Accu-Chek")
            accu_box = BoxLayout(orientation="vertical", spacing=8, padding=8)
            accu_box.add_widget(
                make_path_row("Path Accu-Chek", "acc_root", self.app_config.acc_root)
            )
            accu_box.add_widget(make_fields_grid(ACCU_FIELDS))
            accu.add_widget(accu_box)
            panel.add_widget(accu)

            fit = TabbedPanelItem(text="Google Fit")
            fit_box = BoxLayout(orientation="vertical", spacing=8, padding=8)
            fit_box.add_widget(
                make_path_row("Path Google Fit", "fit_root", self.app_config.fit_root)
            )
            fit_box.add_widget(make_fields_grid(FIT_FIELDS))
            fit.add_widget(fit_box)
            panel.add_widget(fit)

            base = TabbedPanelItem(text="Base")
            base_box = BoxLayout(orientation="vertical", spacing=8, padding=8)
            base_box.add_widget(make_fields_grid(BASE_FIELDS))
            base.add_widget(base_box)
            panel.add_widget(base)

            footer = BoxLayout(orientation="horizontal", size_hint_y=None, height=42)
            cancel_btn = Button(text="Cancelar")
            save_btn = Button(text="Guardar")
            footer.add_widget(cancel_btn)
            footer.add_widget(save_btn)

            content = BoxLayout(orientation="vertical")
            content.add_widget(panel)
            content.add_widget(footer)
            popup = Popup(
                title="Configuracion",
                content=content,
                size_hint=(0.92, 0.92),
            )
            cancel_btn.bind(on_press=lambda *_args: popup.dismiss())
            save_btn.bind(
                on_press=lambda *_args: self._save_popup_config(
                    popup, path_inputs, field_checks
                )
            )
            popup.open()

        def _open_path_chooser(self, target_input: TextInput) -> None:
            start_dir = (
                str(Path(target_input.text).expanduser())
                if target_input.text.strip()
                else str(Path.home())
            )
            chooser = FileChooserListView(path=start_dir, dirselect=True)
            buttons = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)
            cancel_btn = Button(text="Cancelar")
            use_btn = Button(text="Usar carpeta")
            buttons.add_widget(cancel_btn)
            buttons.add_widget(use_btn)

            content = BoxLayout(orientation="vertical")
            content.add_widget(chooser)
            content.add_widget(buttons)
            popup = Popup(
                title="Seleccionar carpeta",
                content=content,
                size_hint=(0.9, 0.9),
            )
            cancel_btn.bind(on_press=lambda *_args: popup.dismiss())

            def apply_selection(*_: object) -> None:
                selected = chooser.selection[0] if chooser.selection else chooser.path
                target_input.text = selected
                popup.dismiss()

            use_btn.bind(on_press=apply_selection)
            chooser.bind(on_submit=lambda *_args: apply_selection())
            popup.open()

        def _save_popup_config(
            self,
            popup: Popup,
            path_inputs: dict[str, TextInput],
            field_checks: dict[str, CheckBox],
        ) -> None:
            selected = [
                field for field, checkbox in field_checks.items() if checkbox.active
            ]
            if not selected:
                selected = ["date", "datetime"]
            self.app_config = AppConfig(
                acc_root=path_inputs["acc_root"].text.strip(),
                fit_root=path_inputs["fit_root"].text.strip(),
                export_dir=path_inputs["export_dir"].text.strip(),
                selected_fields=selected,
            )
            self.store.save_config(self.app_config)
            popup.dismiss()
            if self.status is not None:
                self.status.text = "Configuracion guardada."
            if not self.current_df.empty:
                self._refresh_preview()

        def _on_process(self, _: object) -> None:
            config = self.app_config
            try:
                acc = AccuChekSource(
                    AccuChekPaths(root=Path(config.acc_root).expanduser())
                )
                fit = GoogleFitSource(
                    GoogleFitPaths(root=Path(config.fit_root).expanduser())
                )
                acc.validate()
                fit.validate()

                acc_file = acc.newest_json()
                readings = acc.load_readings(acc_file)
                fit_csvs = fit.daily_metrics_files()
                fit_daily = fit.load_daily(fit_csvs)
                glucose_events = readings_to_frame(readings)
                consolidated = consolidate_readings(
                    glucose_events=glucose_events,
                    fit_daily=fit_daily,
                )
                run_id = self.store.save_processed_run(
                    consolidated,
                    acc_root=config.acc_root,
                    fit_root=config.fit_root,
                    acc_file=str(acc_file),
                    fit_files_count=len(fit_csvs),
                )
            except Exception as exc:
                self._show_error("procesar", exc)
                return

            self.current_df = consolidated
            self._refresh_preview()
            if run_id is None:
                if self.status is not None:
                    self.status.text = (
                        "Sin cambios: esos datos ya estaban procesados en SQLite."
                    )
                return
            self.current_run_id = run_id
            if self.status is not None:
                self.status.text = f"OK. Corrida {run_id} guardada."

        def _on_export(self, _: object) -> None:
            config = self.app_config
            self.store.save_config(config)
            if self.current_df.empty and self.current_run_id is None:
                self._load_latest_run()
            if self.current_df.empty:
                if self.status is not None:
                    self.status.text = "No hay datos para exportar."
                return

            export_df = _filter_columns(self.current_df, config.selected_fields)
            out_dir = (
                Path(config.export_dir).expanduser()
                if config.export_dir
                else Path.cwd() / "salidas"
            )
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            out_path = out_dir / f"salud_consolidada_gui_{timestamp}.xlsx"
            try:
                write_doctor_xlsx(export_df, out_path, ExcelLayout())
            except Exception as exc:
                self._show_error("exportar", exc)
                return
            if self.status is not None:
                self.status.text = f"Excel generado: {out_path}"

        def _load_latest_run(self) -> None:
            run_id = self.store.latest_run_id()
            if run_id is None:
                return
            self.current_run_id = run_id
            self.current_df = self.store.load_run_dataframe(run_id)
            self._refresh_preview()
            if self.status is not None:
                self.status.text = f"Corrida cargada desde SQLite: {run_id}"

        def _refresh_preview(self) -> None:
            if self.preview is None:
                return
            selected = self.app_config.selected_fields
            visible_df = _filter_columns(self.current_df, selected)
            if visible_df.empty:
                self.preview.text = ""
                return
            display_df = _display_frame(visible_df.head(120))
            self.preview.text = display_df.to_string(
                index=False,
                max_colwidth=28,
            )

        def _show_error(self, action: str, exc: Exception) -> None:
            error_type = type(exc).__name__
            if self.status is not None:
                self.status.text = f"Error al {action} ({error_type}): {exc}"
            if self.preview is not None:
                self.preview.text = traceback.format_exc()

    SaludToolApp().run()
    return 0


def _filter_columns(df: pd.DataFrame, selected_fields: list[str]) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    cols = [field for field in selected_fields if field in df.columns]
    cols = _prioritize_date_columns(cols)
    if not cols:
        return df.copy()
    return df.loc[:, cols].copy()


def _prioritize_date_columns(cols: list[str]) -> list[str]:
    priority = ["date", "datetime"]
    ordered = [name for name in priority if name in cols]
    ordered.extend([name for name in cols if name not in priority])
    return ordered


def _display_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare a string-renderable DataFrame for aligned preview."""
    if df.empty:
        return df.copy()
    out = df.copy()
    for col in out.columns:
        out[col] = out[col].map(_format_preview_value)
    return out


def _format_preview_value(value: object) -> str:
    """Format preview values without NaN/scientific notation."""
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        ts = value.tz_localize(None) if value.tzinfo is not None else value
        return ts.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, datetime):
        dt_value = value.replace(tzinfo=None) if value.tzinfo is not None else value
        return dt_value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        text = format(value, "f").rstrip("0").rstrip(".")
        return text if text else "0"
    return str(value)
