"""Baja las dos fuentes de CONAGUA que usamos para contrastar a NASA POWER y las guarda en demos/.

1. Monitor de Sequía de México (SMN): categoría D0–D4 de cada municipio, mensual desde 2003 y quincenal
   desde 2014. Salida: demos/conagua_monitor_sequia.csv (fecha × clave INEGI del municipio).
2. Estadística mensual de estaciones climatológicas del SMN: lluvia total de cada mes.
   Salida: demos/conagua_estaciones.csv (metadatos) y demos/conagua_lluvia_estaciones.csv (fecha × estación, mm).

Las estaciones se eligieron revisando las claves 14001–14420 de Jalisco: las que están en uno de los 20
municipios de Los Altos y tienen 20 años completos o más entre 1991 y 2024.

Uso:  python scripts/descargar_conagua.py      (necesita openpyxl solo aquí: pip install openpyxl)
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent.parent
DEMOS = RAIZ / "demos"
URL_MSM = "https://smn.conagua.gob.mx/tools/RESOURCES/Monitor%20de%20Sequia%20en%20Mexico/MunicipiosSequia.xlsx"
URL_ESTACION = "https://smn.conagua.gob.mx/tools/RESOURCES/Normales_Climatologicas/Mensuales/jal/mes{}.txt"
ESTACIONES = [14006, 14033, 14054, 14076, 14080, 14083, 14084, 14087, 14100, 14101,
              14122, 14123, 14145, 14157, 14165, 14179, 14266, 14320, 14337, 14369]
MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]


def municipios() -> dict[str, dict]:
    """Clave INEGI -> {nombre, zona} de los 20 municipios, desde el polígono de la región."""
    g = json.loads((RAIZ / "data" / "region" / "los_altos.geojson").read_text(encoding="utf-8"))
    return {f["properties"]["cvegeo"]: {"nombre": f["properties"]["nombre"], "zona": f["properties"]["zona"]}
            for f in g["features"] if f["properties"]["tipo"] == "municipio"}


def monitor_sequia(claves: dict[str, dict]) -> pd.DataFrame:
    r = requests.get(URL_MSM, timeout=120)
    r.raise_for_status()
    hoja = pd.read_excel(io.BytesIO(r.content), sheet_name="MUNICIPIOS", dtype={"CVE_CONCATENADA": str})
    hoja = hoja[hoja["CVE_CONCATENADA"].str.zfill(5).isin(claves)].set_index("CVE_CONCATENADA")
    fechas = [c for c in hoja.columns if isinstance(c, pd.Timestamp) or hasattr(c, "year")]
    tabla = hoja[fechas].T
    tabla.index = pd.to_datetime(tabla.index).normalize()
    tabla.index.name = "fecha"
    tabla = tabla.apply(lambda c: c.astype("string").str.strip().where(lambda v: v.str.match(r"^D[0-4]$"), ""))
    faltan = set(claves) - set(tabla.columns)
    if faltan:
        raise ValueError(f"El Monitor de Sequía no trae estos municipios: {sorted(faltan)}")
    return tabla[sorted(claves)]


def estacion(clave: int) -> tuple[dict, pd.Series]:
    r = requests.get(URL_ESTACION.format(clave), timeout=60)
    r.raise_for_status()
    texto = r.content.decode("utf-8", errors="replace")
    cab = {}
    for linea in texto.splitlines()[:25]:
        if ":" in linea:
            k, v = linea.split(":", 1)
            cab[k.strip()] = v.replace("°", "").strip()
    bloque = texto.split("LLUVIA TOTAL MENSUAL", 1)[1].split("\n\n", 1)[0]
    valores = {}
    for linea in bloque.splitlines():
        partes = linea.rstrip("\r").split("\t")
        if not partes[0].isdigit():
            continue
        for i, v in enumerate(partes[1:13]):
            if v.strip():
                valores[pd.Timestamp(int(partes[0]), i + 1, 1)] = float(v)
    meta = {"clave": clave, "nombre": cab["NOMBRE"], "municipio": cab["MUNICIPIO"], "situacion": cab["SITUACIÓN"],
            "lat": float(cab["LATITUD"]), "lon": float(cab["LONGITUD"]), "altitud_m": cab["ALTITUD"].split()[0]}
    return meta, pd.Series(valores, name=str(clave), dtype=float)


def main() -> None:
    claves = municipios()
    msm = monitor_sequia(claves)
    msm.to_csv(DEMOS / "conagua_monitor_sequia.csv")
    print(f"Monitor de Sequía: {len(msm)} fechas ({msm.index.min():%Y-%m} a {msm.index.max():%Y-%m}), "
          f"{msm.shape[1]} municipios")

    por_nombre = {v["nombre"].upper(): v["zona"] for v in claves.values()}
    metas, series = [], []
    for clave in ESTACIONES:
        meta, serie = estacion(clave)
        meta["zona"] = next((z for n, z in por_nombre.items() if n == meta["municipio"].upper()), "")
        metas.append(meta)
        series.append(serie)
    meta = pd.DataFrame(metas)
    if (meta["zona"] == "").any():
        raise ValueError(f"Estaciones sin zona: {meta.loc[meta['zona'] == '', 'nombre'].tolist()}")
    meta.to_csv(DEMOS / "conagua_estaciones.csv", index=False)
    lluvia = pd.concat(series, axis=1).sort_index().loc["1981-01-01":"2024-12-01"]
    lluvia.index.name = "fecha"
    lluvia.round(1).to_csv(DEMOS / "conagua_lluvia_estaciones.csv")
    print(f"Estaciones: {len(meta)} ({meta['zona'].value_counts().to_dict()}), "
          f"{lluvia.notna().sum().sum()} meses con dato de 1981 a 2024")


if __name__ == "__main__":
    main()
