"""Descarga de series mensuales de NASA POWER para Los Altos, con caché en data/ y respaldo sin internet en demos/.

Unidades (contrato): lluvia en mm por mes (POWER da mm/día: × días del mes) y humedad del suelo en
% de saturación (POWER da 0–1: × 100). Los meses sin dato quedan NaN, nunca 0.
"""

from __future__ import annotations

import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from src.catalogo import VARIABLES, obtener_variable
from src.region import celdas, obtener_zona

URL_POWER = "https://power.larc.nasa.gov/api/temporal/monthly/point"
CARPETA_DATOS = Path(__file__).resolve().parent.parent / "data"
CARPETA_DEMOS = Path(__file__).resolve().parent.parent / "demos"
TIMEOUT_S = 60
VALOR_FALTANTE = -999
PESO_MINIMO = 0.5  # un mes de la zona queda NaN si faltan celdas que sumen más de la mitad del peso
# Los datos de 1981–2024 ya no cambian y vienen en demos/: se usan primero (carga instantánea) y solo se
# descarga de POWER lo que no esté ahí. scripts/generar_demos.py lo apaga para bajar todo de nuevo.
USAR_GUARDADOS = True


# ---------- validación ----------

def _validar_coordenadas(lat: float, lon: float) -> None:
    if not -90 <= lat <= 90:
        raise ValueError(f"La latitud {lat} no es válida: debe estar entre -90 y 90.")
    if not -180 <= lon <= 180:
        raise ValueError(f"La longitud {lon} no es válida: debe estar entre -180 y 180.")


def _validar_anios(variable: dict, anio_inicio: int, anio_fin: int) -> None:
    if anio_inicio > anio_fin:
        raise ValueError(f"El año de inicio ({anio_inicio}) no puede ser mayor que el año final ({anio_fin}).")
    if anio_inicio < variable["anio_inicio"] or anio_fin > variable["anio_fin"]:
        raise ValueError(
            f"Para '{variable['id']}' solo hay datos de {variable['anio_inicio']} a {variable['anio_fin']}; "
            f"pediste {anio_inicio}–{anio_fin}."
        )


# ---------- descarga, limpieza y unidades ----------

def _pedir_json(params: dict) -> dict:
    """Hace la petición a POWER con timeout y un reintento."""
    ultimo_error: Exception | None = None
    for intento in range(2):
        try:
            resp = requests.get(URL_POWER, params=params, timeout=TIMEOUT_S)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as error:
            ultimo_error = error
            if intento == 0:
                time.sleep(2)
    raise ConnectionError(f"No se pudo descargar de NASA POWER: {ultimo_error}") from ultimo_error


def _json_a_serie(datos: dict, parametro: str, id_variable: str) -> pd.Series:
    """Respuesta de POWER → serie mensual en las unidades de POWER: sin mes 13 y con -999 como NaN."""
    try:
        valores = datos["properties"]["parameter"][parametro]
    except (KeyError, TypeError) as error:
        raise ValueError(f"La respuesta de NASA POWER no trae el parámetro {parametro}.") from error
    fill = datos.get("header", {}).get("fill_value", VALOR_FALTANTE)

    fechas, numeros = [], []
    for clave, valor in valores.items():
        mes = int(clave[4:6])
        if mes == 13:  # promedio anual: se descarta
            continue
        fechas.append(pd.Timestamp(year=int(clave[:4]), month=mes, day=1))
        numeros.append(np.nan if valor is None or valor == fill or valor == VALOR_FALTANTE else float(valor))

    serie = pd.Series(numeros, index=pd.DatetimeIndex(fechas), name=id_variable, dtype=float)
    return serie.sort_index()


def a_unidades_app(serie: pd.Series, tipo: str) -> pd.Series:
    """mm/día → mm/mes (lluvia) y fracción 0–1 → % de saturación (humedad). NaN se queda NaN."""
    if tipo == "lluvia":  # multiplicar por un Index borra el nombre: se le vuelve a poner
        return (serie * np.asarray(serie.index.days_in_month, dtype=float)).rename(serie.name)
    if tipo == "humedad":
        return serie * 100
    raise ValueError(f"Tipo de variable desconocido: '{tipo}'.")


def _ruta_cache(id_variable: str, lat: float, lon: float, anio_inicio: int, anio_fin: int) -> Path:
    # data/power/ guarda ya en unidades de la app (la caché vieja en mm/día estaba en data/ directo)
    return CARPETA_DATOS / "power" / f"{id_variable}_{lat:.3f}_{lon:.3f}_{anio_inicio}_{anio_fin}.csv"


def _leer_csv(ruta: Path, id_variable: str) -> pd.Series:
    tabla = pd.read_csv(ruta, index_col=0, parse_dates=True)
    serie = tabla.iloc[:, 0].astype(float)
    serie.index = pd.DatetimeIndex(serie.index)
    serie.index.name = None
    serie.name = id_variable
    return serie


# ---------- respaldo sin internet (demos/) ----------

def ruta_demo(id_variable: str, id_zona: str) -> Path:
    """Archivo de respaldo de una variable en una zona (1981–2024)."""
    return CARPETA_DEMOS / f"power_{id_variable}_{id_zona}.csv"


def _respaldo(id_variable: str, id_zona: str, anio_inicio: int, anio_fin: int) -> pd.Series | None:
    ruta = ruta_demo(id_variable, id_zona)
    if not ruta.exists():
        return None
    serie = _leer_csv(ruta, id_variable)
    return serie[(serie.index.year >= anio_inicio) & (serie.index.year <= anio_fin)]


def ruta_demo_celdas(id_variable: str) -> Path:
    """Respaldo de cada celda de POWER de la región (una columna por celda "lat_lon"), para el mapa."""
    return CARPETA_DEMOS / f"celdas_{id_variable}.csv"


def columna_celda(lat: float, lon: float) -> str:
    return f"{lat:.3f}_{lon:.3f}"


def _respaldo_celda(id_variable: str, lat: float, lon: float, anio_inicio: int, anio_fin: int) -> pd.Series | None:
    ruta = ruta_demo_celdas(id_variable)
    if not ruta.exists():
        return None
    tabla = pd.read_csv(ruta, index_col=0, parse_dates=True)
    if columna_celda(lat, lon) not in tabla:
        return None
    serie = tabla[columna_celda(lat, lon)].astype(float).rename(id_variable)
    serie.index = pd.DatetimeIndex(serie.index)
    serie.index.name = None
    return serie[(serie.index.year >= anio_inicio) & (serie.index.year <= anio_fin)]


def _cubre(serie: pd.Series | None, anio_inicio: int, anio_fin: int) -> bool:
    """¿La serie guardada trae todos los años pedidos?"""
    return (serie is not None and not serie.empty and serie.index.year.min() <= anio_inicio
            and serie.index.year.max() >= anio_fin)


# ---------- API pública ----------

def serie_punto(id_variable: str, lat: float, lon: float, anio_inicio: int, anio_fin: int) -> pd.Series:
    """Serie mensual de una variable en una celda de POWER, en mm/mes o % de saturación.

    Orden: caché en data/ → datos guardados en demos/ → descarga de NASA POWER (y, si no hay red, lo que
    haya en demos/ con un aviso).
    """
    variable = obtener_variable(id_variable)
    _validar_coordenadas(lat, lon)
    _validar_anios(variable, anio_inicio, anio_fin)

    ruta = _ruta_cache(id_variable, lat, lon, anio_inicio, anio_fin)
    if ruta.exists():
        return _leer_csv(ruta, id_variable)
    if USAR_GUARDADOS:
        guardada = _respaldo_celda(id_variable, lat, lon, anio_inicio, anio_fin)
        if _cubre(guardada, anio_inicio, anio_fin):
            return guardada

    # Una sola petición trae las 4 variables de la celda; se guardan todas en la caché.
    params = {
        "parameters": ",".join(v["parametro_power"] for v in VARIABLES.values()),
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": anio_inicio,
        "end": anio_fin,
        "format": "JSON",
    }
    try:
        respuesta = _pedir_json(params)
    except ConnectionError:
        respaldo = _respaldo_celda(id_variable, lat, lon, anio_inicio, anio_fin)
        if respaldo is None:
            raise
        warnings.warn(
            f"Sin conexión con NASA POWER: se usan datos guardados en demos/ ({anio_inicio}–{anio_fin}).",
            stacklevel=2,
        )
        return respaldo
    traidas = respuesta.get("properties", {}).get("parameter", {}) if isinstance(respuesta, dict) else {}
    for otra in VARIABLES.values():
        if otra["parametro_power"] in traidas and otra["id"] != id_variable:
            r = _ruta_cache(otra["id"], lat, lon, anio_inicio, anio_fin)
            r.parent.mkdir(parents=True, exist_ok=True)
            a_unidades_app(_json_a_serie(respuesta, otra["parametro_power"], otra["id"]), otra["tipo"]).to_csv(
                r, header=True)
    serie = a_unidades_app(_json_a_serie(respuesta, variable["parametro_power"], id_variable), variable["tipo"])
    ruta.parent.mkdir(parents=True, exist_ok=True)
    serie.to_csv(ruta, header=True)
    return serie


def promedio_ponderado(series: list[pd.Series], pesos: list[float], id_variable: str) -> pd.Series:
    """Promedio por mes con pesos; NaN si las celdas con dato no llegan a la mitad del peso total."""
    tabla = pd.concat(series, axis=1)
    w = np.asarray(pesos, dtype=float)
    con_dato = tabla.notna().to_numpy()
    peso_ok = (con_dato * w).sum(axis=1)
    suma = (np.nan_to_num(tabla.to_numpy()) * w).sum(axis=1)
    valores = np.where(peso_ok > PESO_MINIMO * w.sum(), suma / np.where(peso_ok > 0, peso_ok, 1), np.nan)
    return pd.Series(valores, index=tabla.index, name=id_variable, dtype=float)


def serie_zona(id_variable: str, id_zona: str, anio_inicio: int, anio_fin: int) -> pd.Series:
    """Promedio ponderado (por área) de las celdas de POWER que cubren la zona.

    Si la serie de la zona ya está en demos/ (1981–2024), sale de ahí sin descargar nada. Si no, se arma con
    las celdas; sin internet usa lo que haya en demos/ y avisa con warnings.warn; sin nada, ConnectionError.
    """
    variable = obtener_variable(id_variable)
    obtener_zona(id_zona)
    _validar_anios(variable, anio_inicio, anio_fin)
    if USAR_GUARDADOS:
        guardada = _respaldo(id_variable, id_zona, anio_inicio, anio_fin)
        if _cubre(guardada, anio_inicio, anio_fin):
            return guardada

    lista = celdas(id_zona)
    try:
        series = [serie_punto(id_variable, c["lat"], c["lon"], anio_inicio, anio_fin) for c in lista]
    except ConnectionError:
        respaldo = _respaldo(id_variable, id_zona, anio_inicio, anio_fin)
        if respaldo is None:
            raise
        warnings.warn(
            f"Sin conexión con NASA POWER: se usan datos guardados en demos/ ({anio_inicio}–{anio_fin}).",
            stacklevel=2,
        )
        return respaldo
    return promedio_ponderado(series, [c["peso"] for c in lista], id_variable)
