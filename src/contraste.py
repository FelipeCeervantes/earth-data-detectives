"""Contraste con fuentes de CONAGUA: estaciones del SMN y Monitor de Sequía de México.

Los datos ya vienen en demos/ (los baja scripts/descargar_conagua.py); la app no los pide en línea.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from src import region

DEMOS = Path(__file__).resolve().parent.parent / "demos"
CATEGORIAS = ("D0", "D1", "D2", "D3", "D4")
EN_SEQUIA = ("D1", "D2", "D3", "D4")  # D0 es "anormalmente seco", todavía no es sequía
MIN_ESTACIONES = 3
UMBRAL_SPI = -1.0  # el mismo de src.indices: -1 o menos es sequía
MAYORIA = 0.5      # sequía oficial en la zona: la mitad de sus municipios o más en D1–D4


@lru_cache(maxsize=1)
def _datos() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    meta = pd.read_csv(DEMOS / "conagua_estaciones.csv", dtype={"clave": str})
    lluvia = pd.read_csv(DEMOS / "conagua_lluvia_estaciones.csv", index_col="fecha", parse_dates=True)
    msm = pd.read_csv(DEMOS / "conagua_monitor_sequia.csv", index_col="fecha", parse_dates=True, dtype=str)
    return meta, lluvia, msm.fillna("")


def estaciones(id_zona: str) -> pd.DataFrame:
    """Estaciones del SMN de la zona: clave, nombre, municipio, situación, lat, lon, altitud y zona."""
    region.obtener_zona(id_zona)
    meta = _datos()[0]
    return meta if id_zona == "los-altos" else meta[meta["zona"] == id_zona].reset_index(drop=True)


def lluvia_estaciones(id_zona: str) -> pd.Series:
    """Lluvia mensual (mm) promedio de las estaciones de la zona; NaN si reportan menos de la mitad (mínimo 3)."""
    claves = estaciones(id_zona)["clave"].tolist()
    tabla = _datos()[1][claves]
    minimo = max(MIN_ESTACIONES, len(claves) // 2)
    return tabla.mean(axis=1).where(tabla.notna().sum(axis=1) >= minimo).rename("estaciones")


def comparar_lluvia(power: pd.Series, estaciones_mm: pd.Series) -> dict | None:
    """Compara la lluvia anual de POWER con la de las estaciones, solo en años con los 12 meses en ambas.

    r_anual: correlación de los totales anuales (1 = suben y bajan juntas). diferencia_pct: cuánto más (+) o
    menos (−) llueve en POWER que en las estaciones, en promedio. None si hay menos de 5 años comparables.
    """
    juntos = pd.concat([power, estaciones_mm], axis=1, keys=["power", "estaciones"]).dropna()
    meses = juntos.groupby(juntos.index.year).size()
    anual = juntos.groupby(juntos.index.year).sum()[meses == 12]
    if len(anual) < 5:
        return None
    return {"anios": len(anual), "r_anual": float(anual.corr().iloc[0, 1]),
            "diferencia_pct": float((anual["power"].mean() / anual["estaciones"].mean() - 1) * 100),
            "anual": anual}


def monitor(id_zona: str) -> pd.DataFrame:
    """Último reporte de cada mes del Monitor de Sequía: municipios de la zona en cada categoría y la fracción
    en sequía (D1–D4). Índice: primer día del mes, como las series de POWER."""
    claves = [f["properties"]["cvegeo"] for f in region.contorno(id_zona)["features"]
              if f["properties"]["tipo"] == "municipio"]
    msm = _datos()[2][claves]
    msm = msm.groupby(msm.index.to_period("M")).last()
    msm.index = msm.index.to_timestamp()
    tabla = pd.DataFrame({c: (msm == c).sum(axis=1) for c in CATEGORIAS})
    tabla["total"] = len(claves)
    tabla["fraccion_sequia"] = tabla[list(EN_SEQUIA)].sum(axis=1) / len(claves)
    return tabla


def comparar_sequia(spi: pd.Series, fraccion_sequia: pd.Series) -> dict | None:
    """Coincidencia entre nuestro SPI y el Monitor de Sequía en los meses que tienen los dos.

    confirmados: meses con SPI en sequía en los que el Monitor también tenía a la mayoría de la zona en D1–D4.
    None si no hay meses en común (el Monitor empieza en 2003).
    """
    juntos = pd.concat([spi, fraccion_sequia], axis=1, keys=["spi", "msm"]).dropna()
    if juntos.empty:
        return None
    nuestro, oficial = juntos["spi"] <= UMBRAL_SPI, juntos["msm"] >= MAYORIA
    return {"meses": len(juntos), "meses_spi": int(nuestro.sum()), "meses_oficial": int(oficial.sum()),
            "confirmados": int((nuestro & oficial).sum()),
            "pct_confirmados": float((nuestro & oficial).sum() / nuestro.sum() * 100) if nuestro.any() else np.nan,
            "desde": juntos.index[0], "hasta": juntos.index[-1]}
