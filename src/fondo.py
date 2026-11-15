"""Fondo 3D: el relieve real de Los Altos (puntos de luz), su contorno y lluvia, con three.js.

Se dibuja en un iframe (components.html) que la CSS de src/estilo.py fija detrás de todo el contenido.
Los datos vienen de data/region/relieve.json (scripts/preparar_relieve.py). Si no hay WebGL, no pasa nada:
queda el cielo de la CSS. En el celular o con "reducir movimiento" se dibuja un solo cuadro, sin animación.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ARCHIVO_RELIEVE = Path(__file__).resolve().parent.parent / "data" / "region" / "relieve.json"
THREE = "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"

_HTML = """<!doctype html><html><head><meta charset="utf-8">
<style>html,body{margin:0;height:100%;overflow:hidden;background:transparent}canvas{display:block}</style>
<script type="importmap">{"imports":{"three":"__THREE__"}}</script></head><body>
<script type="module">
import * as THREE from "three";
const R = __RELIEVE__;
try {
  const quieto = matchMedia("(prefers-reduced-motion: reduce)").matches || innerWidth < 700;
  const renderer = new THREE.WebGLRenderer({antialias: true, alpha: true, powerPreference: "low-power"});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.setSize(innerWidth, innerHeight);
  renderer.setClearColor(0x000000, 0);
  document.body.appendChild(renderer.domElement);

  const escena = new THREE.Scene();
  escena.fog = new THREE.Fog(0x0b2b52, 26, 62);
  const camara = new THREE.PerspectiveCamera(36, innerWidth / innerHeight, 0.1, 200);

  // Relieve: 1 unidad = 10 km; la altura va exagerada para que se lean los Altos
  const kmLon = 111.32 * Math.cos((R.sur + R.norte) / 2 * Math.PI / 180);
  const ancho = (R.este - R.oeste) * kmLon / 10, fondo = (R.norte - R.sur) * 111.32 / 10;
  const minimo = Math.min(...R.alturas.flat()), maximo = Math.max(...R.alturas.flat());
  const alto = m => (m - minimo) / 1000 * 1.9;
  const aXYZ = (lon, lat, m) => [(lon - R.oeste) / (R.este - R.oeste) * ancho - ancho / 2, alto(m),
                                  (R.norte - lat) / (R.norte - R.sur) * fondo - fondo / 2];

  const pos = [], col = [];
  const bajo = new THREE.Color(0x1d63a3), medio = new THREE.Color(0x5cc8ff), cima = new THREE.Color(0xf3f8fd);
  for (let i = 0; i < R.filas; i++) for (let j = 0; j < R.columnas; j++) {
    const lon = R.oeste + (R.este - R.oeste) * j / (R.columnas - 1);
    const lat = R.norte - (R.norte - R.sur) * i / (R.filas - 1);
    const m = R.alturas[i][j];
    pos.push(...aXYZ(lon, lat, m));
    const t = (m - minimo) / (maximo - minimo);
    const c = t < 0.55 ? bajo.clone().lerp(medio, t / 0.55) : medio.clone().lerp(cima, (t - 0.55) / 0.45);
    col.push(c.r, c.g, c.b);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  const puntos = new THREE.Points(geo, new THREE.PointsMaterial({size: 0.085, vertexColors: true, transparent: true,
    opacity: 0.9, depthWrite: false, blending: THREE.AdditiveBlending}));

  // Curvas de nivel suaves: una línea de cada 4 filas
  const lineas = [];
  for (let i = 0; i < R.filas; i += 4) for (let j = 0; j < R.columnas - 1; j++) {
    const a = (i * R.columnas + j) * 3, b = a + 3;
    lineas.push(pos[a], pos[a + 1], pos[a + 2], pos[b], pos[b + 1], pos[b + 2]);
  }
  const geoL = new THREE.BufferGeometry();
  geoL.setAttribute("position", new THREE.Float32BufferAttribute(lineas, 3));
  const malla = new THREE.LineSegments(geoL, new THREE.LineBasicMaterial({color: 0x5cc8ff, transparent: true,
    opacity: 0.16, depthWrite: false, blending: THREE.AdditiveBlending}));

  // Contorno de Los Altos, apenas arriba del suelo
  const alturaEn = (lon, lat) => {
    const j = Math.round((lon - R.oeste) / (R.este - R.oeste) * (R.columnas - 1));
    const i = Math.round((R.norte - lat) / (R.norte - R.sur) * (R.filas - 1));
    return R.alturas[Math.max(0, Math.min(R.filas - 1, i))][Math.max(0, Math.min(R.columnas - 1, j))];
  };
  const borde = R.contorno.map(([lon, lat]) => { const p = aXYZ(lon, lat, alturaEn(lon, lat)); p[1] += 0.12; return p; });
  borde.push(borde[0]);
  const contorno = new THREE.Line(new THREE.BufferGeometry().setFromPoints(borde.map(p => new THREE.Vector3(...p))),
    new THREE.LineBasicMaterial({color: 0xffd48a, transparent: true, opacity: 0.85}));

  // Lluvia: gotas como trazos finos que caen y vuelven a empezar arriba
  const N = 900, gotas = new Float32Array(N * 6), vel = new Float32Array(N);
  const nueva = (k, arriba) => {
    const x = (Math.random() - 0.5) * ancho * 1.3, z = (Math.random() - 0.5) * fondo * 1.3;
    const y = arriba ? 9 + Math.random() * 3 : Math.random() * 12;
    gotas.set([x, y, z, x - 0.05, y - 0.42, z], k * 6);
    vel[k] = 5 + Math.random() * 3;
  };
  for (let k = 0; k < N; k++) nueva(k, false);
  const geoG = new THREE.BufferGeometry();
  geoG.setAttribute("position", new THREE.BufferAttribute(gotas, 3));
  const lluvia = new THREE.LineSegments(geoG, new THREE.LineBasicMaterial({color: 0xbfe6ff, transparent: true,
    opacity: 0.22, depthWrite: false}));

  const grupo = new THREE.Group();
  grupo.add(malla, puntos, contorno, lluvia);
  escena.add(grupo);

  const encuadrar = () => {
    const vertical = innerHeight > innerWidth;
    camara.aspect = innerWidth / innerHeight;
    camara.position.set(0, vertical ? 15 : 10.5, vertical ? 40 : 30);
    camara.lookAt(0, vertical ? 7 : 5.2, 0);
    camara.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
  };
  encuadrar();
  addEventListener("resize", () => { encuadrar(); if (quieto) renderer.render(escena, camara); });

  let antes = performance.now(), t = 0, corriendo = false;
  const cuadro = ahora => {
    if (document.hidden) { corriendo = false; return; }  // pestaña oculta: no gasta batería
    const dt = Math.min(0.05, (ahora - antes) / 1000);
    if (dt < 1 / 30) { requestAnimationFrame(cuadro); return; }  // unos 30 cuadros por segundo bastan
    antes = ahora; t += dt;
    grupo.rotation.y = -0.38 + Math.sin(t * 0.045) * 0.22;
    for (let k = 0; k < N; k++) {
      const o = k * 6, d = vel[k] * dt;
      gotas[o + 1] -= d; gotas[o + 4] -= d;
      if (gotas[o + 4] < -0.5) nueva(k, true);
    }
    geoG.attributes.position.needsUpdate = true;
    renderer.render(escena, camara);
    requestAnimationFrame(cuadro);
  };
  const seguir = () => {
    if (corriendo || document.hidden) return;
    corriendo = true; antes = performance.now(); requestAnimationFrame(cuadro);
  };
  grupo.rotation.y = -0.38;
  renderer.render(escena, camara);
  if (!quieto) { seguir(); document.addEventListener("visibilitychange", seguir); }
} catch (e) { /* sin WebGL: se queda el cielo de la CSS */ }
</script></body></html>"""


@lru_cache(maxsize=1)
def html() -> str:
    """Página del fondo 3D, con el relieve incrustado (unos 60 KB). Cadena vacía si falta el relieve."""
    if not ARCHIVO_RELIEVE.exists():
        return ""
    relieve = json.loads(ARCHIVO_RELIEVE.read_text(encoding="utf-8"))
    return _HTML.replace("__THREE__", THREE).replace("__RELIEVE__", json.dumps(relieve, separators=(",", ":")))
