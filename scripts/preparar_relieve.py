"""Relieve de Los Altos para el fondo 3D: una malla pequeña de alturas (m) y el contorno de la región.

Fuente: Terrain Tiles de AWS Open Data (formato Terrarium; mezcla SRTM de la NASA, GMTED y otros), sin cuenta.
Salida: data/region/relieve.json  ({oeste, sur, este, norte, columnas, filas, alturas[fila][columna], contorno})

Uso:  python scripts/preparar_relieve.py
"""

from __future__ import annotations

import io
import json
import math
from pathlib import Path

import numpy as np
import requests
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "data" / "region" / "relieve.json"
URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
ZOOM = 9
MARGEN = 0.35            # grados alrededor de la región
COLUMNAS, FILAS = 120, 96


def mosaico(z: int, x: int, y: int) -> np.ndarray:
    r = requests.get(URL.format(z=z, x=x, y=y), timeout=60)
    r.raise_for_status()
    rgb = np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"), dtype=np.float64)
    return rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768


def a_mosaico(lon: float, lat: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def main() -> None:
    g = json.loads((RAIZ / "data" / "region" / "los_altos.geojson").read_text(encoding="utf-8"))
    zona = next(f for f in g["features"] if f["properties"]["tipo"] == "zona" and f["properties"]["id"] == "los-altos")
    poligonos = [zona["geometry"]["coordinates"]] if zona["geometry"]["type"] == "Polygon" \
        else zona["geometry"]["coordinates"]
    puntos = [p for poligono in poligonos for p in poligono[0]]
    oeste, este = min(p[0] for p in puntos) - MARGEN, max(p[0] for p in puntos) + MARGEN
    sur, norte = min(p[1] for p in puntos) - MARGEN, max(p[1] for p in puntos) + MARGEN

    x0, y0 = a_mosaico(oeste, norte, ZOOM)
    x1, y1 = a_mosaico(este, sur, ZOOM)
    tx = range(int(x0), int(x1) + 1)
    ty = range(int(y0), int(y1) + 1)
    grande = np.vstack([np.hstack([mosaico(ZOOM, x, y) for x in tx]) for y in ty])

    alturas = []
    for i in range(FILAS):
        lat = norte - (norte - sur) * i / (FILAS - 1)
        fila = []
        for j in range(COLUMNAS):
            lon = oeste + (este - oeste) * j / (COLUMNAS - 1)
            x, y = a_mosaico(lon, lat, ZOOM)
            px = min(int((x - tx[0]) * 256), grande.shape[1] - 1)
            py = min(int((y - ty[0]) * 256), grande.shape[0] - 1)
            fila.append(int(round(grande[py, px])))
        alturas.append(fila)

    # Contorno simplificado (el anillo exterior más largo, uno de cada 6 puntos)
    anillo = max((poligono[0] for poligono in poligonos), key=len)
    contorno = [[round(lon, 4), round(lat, 4)] for lon, lat in anillo[::6]]
    SALIDA.write_text(json.dumps({"oeste": round(oeste, 4), "sur": round(sur, 4), "este": round(este, 4),
                                  "norte": round(norte, 4), "columnas": COLUMNAS, "filas": FILAS,
                                  "alturas": alturas, "contorno": contorno}, separators=(",", ":")),
                      encoding="utf-8")
    plano = np.array(alturas)
    print(f"Relieve: {COLUMNAS}×{FILAS}, de {plano.min()} a {plano.max()} m; contorno de {len(contorno)} puntos; "
          f"{SALIDA.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
