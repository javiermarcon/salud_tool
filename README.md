# Salud Tool

App Kivy para consolidar datos de **Accu-Chek** y **Google Fit**, persistir todo en **SQLite** y exportar a Excel. Una fila por cada medicion de glucosa con fecha/hora, valor en mg/dL y metricas de actividad del dia (pasos, distancia, calorias, minutos activos).

## ¿Qué hace?

- **Lee** las exportaciones JSON del Accu-Chek (glucosa en sangre).
- **Lee** las métricas diarias de Google Fit (Takeout: pasos, distancia, calorías, minutos activos).
- **Une** cada medicion de glucosa con las metricas del mismo dia.
- **Guarda** configuracion (paths y campos visibles) en SQLite.
- **Guarda** en SQLite todo lo procesado en cada corrida, incluso si no se muestra en pantalla.
- **Permite** elegir campos visibles por fuente y exportar esos campos a `.xlsx`.

El Excel queda pensado para revision medica o para llevar un registro ordenado en una sola hoja.

## Requisitos

- Python **3.12+**
- Datos exportados del Accu-Chek en JSON (`accuchek_*.json`).
- Takeout de Google Fit con las métricas diarias en CSV.

## Estructura de carpetas esperada

Por defecto el programa usa un directorio base (por ejemplo `~/proyectos/salud`). Dentro de él:

```
base_dir/
├── glucosa/
│   └── datos/
│       └── accuchek_YYYY-MM-DD_HH-MM-SS.json   # Exportación Accu-Chek
├── fit/
│   └── Takeout/
│       └── Fit/
│           └── Métricas de actividad diaria/
│               ├── 2025-01-15.csv
│               ├── 2025-01-16.csv
│               └── ...
└── salidas/   # Aquí se guardan los Excel generados
```

- **Accu-Chek**: en `base_dir/glucosa/datos/` debe haber al menos un archivo `accuchek_*.json`. Se usa el más reciente por fecha de modificación.
- **Google Fit**: en `base_dir/fit/Takeout/Fit/Métricas de actividad diaria/` los CSV diarios con pasos, distancia, calorías y minutos activos.
- **Salida**: el Excel se guarda en `base_dir/salidas/` con un nombre tipo `salud_consolidada_diaria_YYYY-MM-DD_HH-MM-SS.xlsx`.

## Instalación

Clonar el repositorio e instalar en modo editable:

```bash
git clone <url-del-repo>
cd salud_tool
pip install -e .
```

Dependencias principales: `kivy`, `pandas`, `openpyxl`, `python-dateutil`.

## Uso

Desde la raiz del proyecto:

```bash
python -m salud_tool
```

Tambien podes ejecutarla asi:

```bash
python app.py
```

La app permite:
- Configurar path de Accu-Chek (directorio con `accuchek_*.json`).
- Configurar path de Google Fit (`.../Takeout/Fit`).
- Configurar directorio de exportacion.
- Elegir campos a mostrar y exportar.
- Procesar datos y guardar corrida en `salud_tool.sqlite3`.

En la pantalla principal tenes el boton `Configuracion`, que abre un menu lateral
con pestañas separadas:
- `General`: directorio de exportacion.
- `Accu-Chek`: path de origen + campos de esa fuente.
- `Google Fit`: path de origen + campos de esa fuente.
- `Base`: campos comunes (`date`, `datetime`).

Los paths se pueden escribir completos o elegir con file browser.
La app incluye boton `Salir`; con `Esc` salis de fullscreen o cerras la app.

## Desarrollo

Instalar dependencias de desarrollo:

```bash
pip install -e ".[dev]"
```

Ejecutar tests:

```bash
pytest
```

Linting y formato (ruff):

```bash
ruff check src tests
ruff format src tests
```

## Licencia

MIT. Ver [LICENSE](LICENSE).
