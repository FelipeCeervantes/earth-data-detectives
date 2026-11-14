"""Guarda en demos/ el respaldo sin internet: 3 zonas × 4 variables y cada celda de POWER (mapa), 1981–2024.

Ejecutar desde la raíz del repo:  python scripts/generar_demos.py
Borra los respaldos viejos de ciudades (power_<variable>_<ciudad>.csv) que ya no aplican.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import datos  # noqa: E402
from src.catalogo import VARIABLES  # noqa: E402
from src.region import ZONAS, celdas  # noqa: E402


def main() -> None:
    datos.USAR_GUARDADOS = False  # bajar de NASA POWER (o de la caché en data/), no leer lo que se va a reescribir
    datos.CARPETA_DEMOS.mkdir(parents=True, exist_ok=True)
    nuevos = {datos.ruta_demo(v, z).name for v in VARIABLES for z in ZONAS}
    nuevos |= {datos.ruta_demo_celdas(v).name for v in VARIABLES}
    for viejo in [*datos.CARPETA_DEMOS.glob("power_*.csv"), *datos.CARPETA_DEMOS.glob("celdas_*.csv")]:
        if viejo.name not in nuevos:
            viejo.unlink()
            print(f"borrado {viejo.name}")

    total, hechos = len(VARIABLES) * len(ZONAS), 0
    for id_variable, variable in VARIABLES.items():
        for id_zona in ZONAS:
            serie = datos.serie_zona(id_variable, id_zona, variable["anio_inicio"], variable["anio_fin"])
            ruta = datos.ruta_demo(id_variable, id_zona)
            serie.round(3).to_csv(ruta, header=True)
            hechos += 1
            print(f"[{hechos}/{total}] {ruta.name}: {serie.notna().sum()} meses con dato, "
                  f"media {serie.mean():.1f} {variable['unidades']}")

    # Cada celda de la región (toda la región contiene las de Norte y Sur), para el mapa sin internet.
    for id_variable, variable in VARIABLES.items():
        columnas = {datos.columna_celda(c["lat"], c["lon"]): datos.serie_punto(
            id_variable, c["lat"], c["lon"], variable["anio_inicio"], variable["anio_fin"]) for c in celdas("los-altos")}
        ruta = datos.ruta_demo_celdas(id_variable)
        pd.DataFrame(columnas).round(3).to_csv(ruta)
        print(f"{ruta.name}: {len(columnas)} celdas")


if __name__ == "__main__":
    main()
