# Salud Tool

Genera un Excel listo para imprimir o compartir con tu médico a partir de los datos del **glucómetro Accu-Chek** y de **Google Fit**. Una fila por cada medición de glucosa, con fecha/hora, valor en mg/dL y las métricas de actividad del día (pasos, distancia, calorías, minutos activos).

## ¿Qué hace?

- **Lee** las exportaciones JSON del Accu-Chek (glucosa en sangre).
- **Lee** las métricas diarias de Google Fit (Takeout: pasos, distancia, calorías, minutos activos).
- **Une** cada medición de glucosa con las métricas del mismo día.
- **Escribe** un archivo `.xlsx` formateado con:
  - Día de la semana (lun, mar, mie…)
  - Fecha / hora de cada medición
  - Glucosa (mg/dL)
  - Pasos, distancia, calorías y minutos activos del día

El Excel queda pensado para revisión médica o para llevar un registro ordenado en una sola hoja.

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

Dependencias principales: `pandas`, `openpyxl`, `python-dateutil`.

## Uso

Desde la raíz del proyecto:

```bash
python -m salud_tool
```

O indicando otro directorio base:

```bash
python -m salud_tool --base-dir /ruta/a/mis/datos
```

Opciones:

| Opción         | Descripción                                      | Por defecto           |
|----------------|---------------------------------------------------|------------------------|
| `--base-dir`   | Directorio base (glucosa, fit, salidas)           | `~/proyectos/salud`   |
| `--days`       | Días hacia atrás (informativo por ahora)          | `365`                  |

Al terminar se imprime la ruta del archivo Accu-Chek usado, la cantidad de CSV de Fit y la ruta del Excel generado.

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
