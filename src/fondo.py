"""Fondo 3D: el relieve real de Los Altos (puntos de luz), su contorno y lluvia, con three.js.

Se dibuja en un iframe (st.iframe) que la CSS de src/estilo.py fija detrás de todo el contenido. La lluvia
tiene profundidad (tres capas y salpicaduras sobre el relieve), es más densa si la temporada del periodo elegido
fue más lluviosa que lo normal (la app lo avisa con la clase .dd-lluvia) y el relieve responde con un parallax
suave al mouse y al scroll.
Los datos vienen de data/region/relieve.json (scripts/preparar_relieve.py). Si no hay WebGL, no pasa nada:
queda el cielo de la CSS. En el celular o con "reducir movimiento" se dibuja un solo cuadro, sin animación.
"""

from __future__ import annotations

import base64
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
const abre = r => {  // alturas: texto base64 con un byte por punto (metros = base + byte × paso)
  const b = atob(r.alturas), H = [];
  for (let i = 0; i < r.filas; i++) {
    const fila = new Array(r.columnas);
    for (let j = 0; j < r.columnas; j++) fila[j] = r.base + b.charCodeAt(i * r.columnas + j) * r.paso;
    H.push(fila);
  }
  r.alturas = H;
  return r;
};
const R = abre(__RELIEVE__);
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

  // Lluvia con profundidad: tres capas. Al fondo, gotas cortas, tenues y lentas; cerca, largas, claras y rápidas.
  // n es el máximo (temporada más lluviosa que lo normal); con lluvia normal se dibuja el 70 %.
  const sueloEn = (x, z) => alto(alturaEn(R.oeste + (x / ancho + 0.5) * (R.este - R.oeste),
                                          R.norte - (z / fondo + 0.5) * (R.norte - R.sur)));
  const capas = [{n: 520, largo: 0.24, vel: 3.2, op: 0.13}, {n: 430, largo: 0.42, vel: 5.4, op: 0.22},
                 {n: 280, largo: 0.72, vel: 8.4, op: 0.34}].map((c, i) => {
    const pos = new Float32Array(c.n * 6), vel = new Float32Array(c.n), suelo = new Float32Array(c.n);
    const nueva = (k, arriba) => {
      const x = (Math.random() - 0.5) * ancho * 1.3, z = (Math.random() - 0.5) * fondo * 1.3;
      const y = arriba ? 9 + Math.random() * 3 : Math.random() * 12;
      pos.set([x, y, z, x - c.largo * 0.12, y - c.largo, z], k * 6);
      vel[k] = c.vel * (0.8 + Math.random() * 0.4);
      suelo[k] = Math.abs(x) < ancho / 2 && Math.abs(z) < fondo / 2 ? sueloEn(x, z) : -0.5;  // -0.5: cae fuera del relieve
    };
    for (let k = 0; k < c.n; k++) nueva(k, false);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    const obj = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({color: 0xbfe6ff, transparent: true,
      opacity: c.op, depthWrite: false}));
    return {n: c.n, activas: c.n, pos, vel, suelo, nueva, geo, obj, salpica: i > 0};
  });

  // Salpicaduras: puntos de luz que se apagan donde una gota toca el relieve
  const S = 80, sPos = new Float32Array(S * 3), sCol = new Float32Array(S * 3), sVida = new Float32Array(S);
  let sSig = 0;
  const geoS = new THREE.BufferGeometry();
  geoS.setAttribute("position", new THREE.BufferAttribute(sPos, 3));
  geoS.setAttribute("color", new THREE.BufferAttribute(sCol, 3));
  const salpicaduras = new THREE.Points(geoS, new THREE.PointsMaterial({size: 0.17, vertexColors: true,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending}));
  const salpica = (x, y, z) => { sPos.set([x, y + 0.04, z], sSig * 3); sVida[sSig] = 1; sSig = (sSig + 1) % S; };

  // Más o menos lluvia según la temporada del periodo elegido: la app deja la señal en la clase .dd-lluvia
  let densidad = 0;
  const leeDensidad = () => {
    let d = 1;
    try {
      const m = parent.document.querySelector(".dd-lluvia");
      if (m) d = m.classList.contains("dd-lluvia--mas") ? 1.43 : m.classList.contains("dd-lluvia--menos") ? 0.6 : 1;
    } catch (e) { /* sin acceso a la página: lluvia normal */ }
    if (d === densidad) return;
    densidad = d;
    for (const c of capas) { c.activas = Math.min(c.n, Math.round(c.n * d * 0.7)); c.geo.setDrawRange(0, c.activas * 2); }
  };
  leeDensidad();

  const grupo = new THREE.Group();
  grupo.add(malla, puntos, contorno, salpicaduras, ...capas.map(c => c.obj));
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

  // Parallax suave: el relieve responde al mouse (solo con mouse) y al scroll de la página
  let mx = 0, my = 0, ms = 0, objX = 0, objY = 0, objS = 0;
  try {
    if (!quieto && parent !== window) {
      const corta = new AbortController(), opciones = {passive: true, signal: corta.signal};
      if (matchMedia("(pointer: fine)").matches) parent.addEventListener("mousemove", e => {
        objX = e.clientX / parent.innerWidth - 0.5; objY = e.clientY / parent.innerHeight - 0.5;
      }, opciones);
      parent.document.addEventListener("scroll", e => {
        const quien = e.target === parent.document ? parent.document.scrollingElement : e.target;
        if (quien && quien.clientHeight > parent.innerHeight * 0.6) objS = Math.min(1, quien.scrollTop / 1800);
      }, {...opciones, capture: true});
      addEventListener("pagehide", () => corta.abort());
    }
  } catch (e) { /* sin acceso a la página: el fondo solo gira despacio */ }

  let antes = performance.now(), t = 0, corriendo = false, revisar = 0;
  const cuadro = ahora => {
    if (document.hidden) { corriendo = false; return; }  // pestaña oculta: no gasta batería
    const dt = Math.min(0.05, (ahora - antes) / 1000);
    if (dt < 1 / 30) { requestAnimationFrame(cuadro); return; }  // unos 30 cuadros por segundo bastan
    antes = ahora; t += dt;
    if (t > revisar) { revisar = t + 1; leeDensidad(); }
    mx += (objX - mx) * 0.05; my += (objY - my) * 0.05; ms += (objS - ms) * 0.08;
    grupo.rotation.y = -0.38 + Math.sin(t * 0.045) * 0.22 + mx * 0.12;
    grupo.rotation.x = my * 0.05;
    grupo.position.set(-mx * 0.9, ms * 1.8, 0);
    for (const c of capas) {
      for (let k = 0; k < c.activas; k++) {
        const o = k * 6, d = c.vel[k] * dt;
        c.pos[o + 1] -= d; c.pos[o + 4] -= d;
        if (c.pos[o + 4] < c.suelo[k]) {
          if (c.salpica && c.suelo[k] > -0.5 && Math.random() < 0.45) salpica(c.pos[o + 3], c.suelo[k], c.pos[o + 5]);
          c.nueva(k, true);
        }
      }
      c.geo.attributes.position.needsUpdate = true;
    }
    for (let k = 0; k < S; k++) {
      if (sVida[k] <= 0) continue;
      sVida[k] = Math.max(0, sVida[k] - dt / 0.42);
      sCol.set([0.55 * sVida[k], 0.8 * sVida[k], sVida[k]], k * 3);
    }
    geoS.attributes.position.needsUpdate = true; geoS.attributes.color.needsUpdate = true;
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
def relieve_compacto() -> dict | None:
    """El relieve con las alturas en un byte por punto (texto base64): pesa unos 15 KB en vez de 60.

    metros = base + byte × paso (paso de unos 8 m: de sobra para dibujar). None si falta el archivo.
    """
    if not ARCHIVO_RELIEVE.exists():
        return None
    r = json.loads(ARCHIVO_RELIEVE.read_text(encoding="utf-8"))
    planas = [m for fila in r["alturas"] for m in fila]
    base, tope = min(planas), max(planas)
    paso = max((tope - base) / 255, 1e-9)
    crudo = bytes(min(255, max(0, round((m - base) / paso))) for m in planas)
    return {"oeste": r["oeste"], "sur": r["sur"], "este": r["este"], "norte": r["norte"], "filas": r["filas"],
            "columnas": r["columnas"], "base": round(base, 1), "paso": round(paso, 4),
            "alturas": base64.b64encode(crudo).decode("ascii"), "contorno": r["contorno"]}


@lru_cache(maxsize=1)
def html() -> str:
    """Página del fondo 3D, con el relieve incrustado (unos 20 KB). Cadena vacía si falta el relieve."""
    relieve = relieve_compacto()
    if relieve is None:
        return ""
    return _HTML.replace("__THREE__", THREE).replace("__RELIEVE__", json.dumps(relieve, separators=(",", ":")))
