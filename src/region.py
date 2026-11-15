"""Región de estudio: los 20 municipios de Los Altos de Jalisco (fase Los Altos).

El contorno viene de data/region/los_altos.geojson (Marco Geoestadístico de INEGI; ver data/region/fuente.md).
Todo en Python puro: la app no necesita librerías de geografía.
"""

from __future__ import annotations

import copy
import json
import math
from functools import lru_cache
from pathlib import Path

ARCHIVO_REGION = Path(__file__).resolve().parent.parent / "data" / "region" / "los_altos.geojson"

# Malla de NASA POWER (MERRA-2): celdas de 0.5° de latitud × 0.625° de longitud, centradas en múltiplos.
PASO_LAT = 0.5
PASO_LON = 0.625
PASO_MUESTREO = 0.025  # malla fina para estimar qué fracción del área cae en cada celda

_NORTE = ["Encarnación de Díaz", "Lagos de Moreno", "Ojuelos de Jalisco", "San Diego de Alejandría",
          "San Juan de los Lagos", "Teocaltiche", "Unión de San Antonio", "Villa Hidalgo"]
_SUR = ["Acatic", "Arandas", "Cañadas de Obregón", "Jalostotitlán", "Jesús María", "Mexticacán",
        "San Ignacio Cerro Gordo", "San Julián", "San Miguel el Alto", "Tepatitlán de Morelos",
        "Valle de Guadalupe", "Yahualica de González Gallo"]

ZONAS: dict[str, dict] = {
    "los-altos": {"id": "los-altos", "nombre": "Toda la región", "municipios": _NORTE + _SUR},
    "altos-norte": {"id": "altos-norte", "nombre": "Altos Norte", "municipios": list(_NORTE)},
    "altos-sur": {"id": "altos-sur", "nombre": "Altos Sur", "municipios": list(_SUR)},
}


NOMBRES_EN = {"los-altos": "Whole region", "altos-norte": "Altos Norte", "altos-sur": "Altos Sur"}


def obtener_zona(id_zona: str, idioma: str = "es") -> dict:
    """Regresa la zona con ese id, con su nombre en el idioma pedido (en/es). ValueError si no existe."""
    if id_zona not in ZONAS:
        raise ValueError(f"La zona '{id_zona}' no existe. Usa una de: {', '.join(ZONAS)}.")
    if idioma not in ("en", "es"):
        raise ValueError(f"Idioma no válido: '{idioma}'. Usa 'en' o 'es'.")
    zona = copy.deepcopy(ZONAS[id_zona])
    if idioma == "en":
        zona["nombre"] = NOMBRES_EN[id_zona]
    return zona


@lru_cache(maxsize=1)
def _geojson() -> dict:
    if not ARCHIVO_REGION.exists():
        raise FileNotFoundError(f"Falta {ARCHIVO_REGION}. Genéralo con scripts/preparar_region.py.")
    return json.loads(ARCHIVO_REGION.read_text(encoding="utf-8"))


def contorno(id_zona: str) -> dict:
    """GeoJSON (FeatureCollection) con el contorno de la zona y sus municipios, para el mapa."""
    obtener_zona(id_zona)
    rasgos = []
    for f in _geojson()["features"]:
        p = f["properties"]
        if p["tipo"] == "zona" and p["id"] == id_zona:
            rasgos.insert(0, f)
        elif p["tipo"] == "municipio" and (id_zona == "los-altos" or p["zona"] == id_zona):
            rasgos.append(f)
    return copy.deepcopy({"type": "FeatureCollection", "features": rasgos})


def _anillos(id_zona: str) -> list[list[list[tuple[float, float]]]]:
    """Polígonos de la zona como listas de anillos [(lon, lat)]; el primero es el borde, los demás, huecos."""
    rasgo = contorno(id_zona)["features"][0]
    geom = rasgo["geometry"]
    poligonos = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return [[[tuple(p) for p in anillo] for anillo in poligono] for poligono in poligonos]


def _dentro_anillo(lon: float, lat: float, anillo: list[tuple[float, float]]) -> bool:
    """Prueba de punto dentro de polígono por cruce de rayos."""
    dentro = False
    j = len(anillo) - 1
    for i in range(len(anillo)):
        xi, yi = anillo[i]
        xj, yj = anillo[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def dentro(lon: float, lat: float, id_zona: str) -> bool:
    """¿El punto (lon, lat) cae dentro de la zona?"""
    for poligono in _anillos(id_zona):
        if _dentro_anillo(lon, lat, poligono[0]) and not any(_dentro_anillo(lon, lat, h) for h in poligono[1:]):
            return True
    return False


def celda_de(lat: float, lon: float) -> tuple[float, float]:
    """Centro de la celda de POWER (MERRA-2) que contiene el punto."""
    return (round(round((lat + 90) / PASO_LAT) * PASO_LAT - 90, 4),
            round(round((lon + 180) / PASO_LON) * PASO_LON - 180, 4))


@lru_cache(maxsize=None)
def _celdas(id_zona: str) -> tuple[tuple[float, float, float], ...]:
    return _pesos(_anillos(id_zona))


def _pesos(poligonos: list) -> tuple[tuple[float, float, float], ...]:
    """Qué fracción del área de los polígonos cae en cada celda de POWER (muestreo en una malla fina)."""
    lons = [p[0] for pol in poligonos for p in pol[0]]
    lats = [p[1] for pol in poligonos for p in pol[0]]
    pesos: dict[tuple[float, float], float] = {}
    lat = math.floor(min(lats) / PASO_MUESTREO) * PASO_MUESTREO + PASO_MUESTREO / 2
    while lat < max(lats):
        area = math.cos(math.radians(lat))  # en grados, una franja más al norte cubre menos área
        lon = math.floor(min(lons) / PASO_MUESTREO) * PASO_MUESTREO + PASO_MUESTREO / 2
        while lon < max(lons):
            if any(_dentro_anillo(lon, lat, pol[0]) and not any(_dentro_anillo(lon, lat, h) for h in pol[1:])
                   for pol in poligonos):
                c = celda_de(lat, lon)
                pesos[c] = pesos.get(c, 0.0) + area
            lon += PASO_MUESTREO
        lat += PASO_MUESTREO
    total = sum(pesos.values())
    return tuple(sorted(((la, lo, p / total) for (la, lo), p in pesos.items()), key=lambda c: (-c[0], c[1])))


def celdas(id_zona: str) -> list[dict]:
    """Celdas de POWER que cubren la zona: [{lat, lon, peso}], peso = fracción del área de la zona (suman 1)."""
    obtener_zona(id_zona)
    return [{"lat": la, "lon": lo, "peso": p} for la, lo, p in _celdas(id_zona)]


@lru_cache(maxsize=None)
def _celdas_municipio(nombre: str) -> tuple[tuple[float, float, float], ...]:
    for f in contorno("los-altos")["features"]:
        if f["properties"]["tipo"] == "municipio" and f["properties"]["nombre"] == nombre:
            g = f["geometry"]
            poligonos = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            return _pesos([[[tuple(p[:2]) for p in anillo] for anillo in pol] for pol in poligonos])
    raise ValueError(f"El municipio '{nombre}' no está en Los Altos.")


def celdas_municipio(nombre: str) -> list[dict]:
    """Celdas de POWER que cubren un municipio: [{lat, lon, peso}], peso = fracción de su área (suman 1)."""
    return [{"lat": la, "lon": lo, "peso": p} for la, lo, p in _celdas_municipio(nombre)]
