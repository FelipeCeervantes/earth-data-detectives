"""Prepara data/region/los_altos.geojson a partir del Marco Geoestadístico de INEGI.

Fuente: INEGI, Marco Geoestadístico, Encuesta Intercensal 2025 (edición 2026), paquete de Jalisco
(14_jalisco.zip, capa de municipios 14mun.shp). Ver data/region/fuente.md.

Uso (desde la raíz del repo, con el zip ya descargado en data/inegi/):
    pip install pyshp shapely        # solo para este script; la app solo lee el GeoJSON
    python scripts/preparar_region.py [ruta/al/14_jalisco.zip]

Qué hace:
1. Lee los 125 municipios de Jalisco (proyección Lambert de INEGI, EPSG:6372, en metros).
2. Filtra los 20 de Los Altos por su nombre oficial (falla si falta alguno).
3. Convierte las coordenadas a longitud/latitud (GRS80 ≈ WGS84) con la fórmula exacta de Lambert.
4. Une los municipios de cada zona (Altos Norte, Altos Sur y toda la región) y simplifica los contornos.
5. Guarda un GeoJSON pequeño con los 20 municipios y las 3 zonas.
"""

from __future__ import annotations

import io
import json
import math
import sys
import zipfile
from pathlib import Path

import numpy as np
import shapefile  # pyshp
import shapely
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

RAIZ = Path(__file__).resolve().parent.parent
ZIP_POR_DEFECTO = RAIZ / "data" / "inegi" / "14_jalisco.zip"
SALIDA = RAIZ / "data" / "region" / "los_altos.geojson"
TOLERANCIA_GRADOS = 0.0015  # ~150 m: el contorno se ve igual y el archivo queda pequeño
DECIMALES = 5               # ~1 m

ALTOS_NORTE = ["Encarnación de Díaz", "Lagos de Moreno", "Ojuelos de Jalisco", "San Diego de Alejandría",
               "San Juan de los Lagos", "Teocaltiche", "Unión de San Antonio", "Villa Hidalgo"]
ALTOS_SUR = ["Acatic", "Arandas", "Cañadas de Obregón", "Jalostotitlán", "Jesús María", "Mexticacán",
             "San Ignacio Cerro Gordo", "San Julián", "San Miguel el Alto", "Tepatitlán de Morelos",
             "Valle de Guadalupe", "Yahualica de González Gallo"]
ZONAS = {"altos-norte": ("Altos Norte", ALTOS_NORTE), "altos-sur": ("Altos Sur", ALTOS_SUR),
         "los-altos": ("Los Altos de Jalisco", ALTOS_NORTE + ALTOS_SUR)}

# --- Lambert Conformal Conic 2SP (EPSG:6372, "Mexico ITRF2008 / LCC") → lon/lat ----------------
_A = 6378137.0
_F = 1 / 298.257222101  # GRS 1980
_E = math.sqrt(2 * _F - _F ** 2)
_FI1, _FI2, _FI0, _LAM0 = map(math.radians, (17.5, 29.5, 12.0, -102.0))
_FE, _FN = 2_500_000.0, 0.0


def _m(fi: float) -> float:
    return math.cos(fi) / math.sqrt(1 - (_E * math.sin(fi)) ** 2)


def _t(fi: float) -> float:
    s = _E * math.sin(fi)
    return math.tan(math.pi / 4 - fi / 2) / ((1 - s) / (1 + s)) ** (_E / 2)


_N = (math.log(_m(_FI1)) - math.log(_m(_FI2))) / (math.log(_t(_FI1)) - math.log(_t(_FI2)))
_FF = _m(_FI1) / (_N * _t(_FI1) ** _N)
_RHO0 = _A * _FF * _t(_FI0) ** _N


def lcc_a_lonlat(x: float, y: float) -> tuple[float, float]:
    """Inversa de Lambert cónica conforme (Snyder, ec. 15-9 a 15-11) para la proyección de INEGI."""
    dx, dy = x - _FE, _RHO0 - (y - _FN)
    rho = math.copysign(math.hypot(dx, dy), _N)
    theta = math.atan2(dx, dy)
    t = (rho / (_A * _FF)) ** (1 / _N)
    fi = math.pi / 2 - 2 * math.atan(t)
    for _ in range(10):  # converge en 3 o 4 vueltas
        s = _E * math.sin(fi)
        fi = math.pi / 2 - 2 * math.atan(t * ((1 - s) / (1 + s)) ** (_E / 2))
    return math.degrees(theta / _N + _LAM0), math.degrees(fi)


def _a_lonlat(coords: np.ndarray) -> np.ndarray:
    return np.array([lcc_a_lonlat(x, y) for x, y in coords])


def _redondear(geom: dict) -> dict:
    def r(c):
        return [r(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], DECIMALES), round(c[1], DECIMALES)]
    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}


def leer_municipios(ruta_zip: Path) -> dict[str, dict]:
    """{nombre: {cvegeo, geom (shapely, lon/lat)}} de los municipios de Jalisco."""
    z = zipfile.ZipFile(ruta_zip)
    lector = shapefile.Reader(
        shp=io.BytesIO(z.read("conjunto_de_datos/14mun.shp")),
        shx=io.BytesIO(z.read("conjunto_de_datos/14mun.shx")),
        dbf=io.BytesIO(z.read("conjunto_de_datos/14mun.dbf")),
        encoding="latin-1",  # 14mun.cpg: ISO 8859-1
    )
    municipios = {}
    for forma in lector.iterShapeRecords():
        geom = shapely.transform(shape(forma.shape.__geo_interface__), _a_lonlat)
        municipios[forma.record["NOMGEO"]] = {"cvegeo": forma.record["CVEGEO"], "geom": geom}
    return municipios


def main(ruta_zip: Path = ZIP_POR_DEFECTO) -> None:
    if not ruta_zip.exists():
        sys.exit(f"No encuentro {ruta_zip}. Descárgalo de INEGI (ver data/region/fuente.md).")
    municipios = leer_municipios(ruta_zip)
    faltan = [n for n in ALTOS_NORTE + ALTOS_SUR if n not in municipios]
    if faltan:
        sys.exit(f"No están en el Marco Geoestadístico: {faltan}")

    rasgos = []
    for id_zona, (nombre, lista) in ZONAS.items():
        union = unary_union([municipios[n]["geom"] for n in lista]).buffer(0)
        simple = union.simplify(TOLERANCIA_GRADOS, preserve_topology=True)
        rasgos.append({"type": "Feature", "properties": {"tipo": "zona", "id": id_zona, "nombre": nombre,
                                                         "municipios": len(lista)},
                       "geometry": _redondear(mapping(simple))})
    for zona_id, lista in (("altos-norte", ALTOS_NORTE), ("altos-sur", ALTOS_SUR)):
        for n in lista:
            simple = municipios[n]["geom"].simplify(TOLERANCIA_GRADOS, preserve_topology=True)
            rasgos.append({"type": "Feature", "properties": {"tipo": "municipio", "nombre": n,
                                                             "cvegeo": municipios[n]["cvegeo"], "zona": zona_id},
                           "geometry": _redondear(mapping(simple))})

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps({"type": "FeatureCollection", "features": rasgos}, ensure_ascii=False,
                                 separators=(",", ":")), encoding="utf-8")
    zona = shape(rasgos[2]["geometry"])
    print(f"{SALIDA.relative_to(RAIZ)}: {SALIDA.stat().st_size / 1024:.0f} KB · {len(rasgos)} rasgos · "
          f"límites de Los Altos {tuple(round(v, 3) for v in zona.bounds)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ZIP_POR_DEFECTO)
