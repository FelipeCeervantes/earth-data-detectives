"""Globo 3D de la sección Panorama: el planeta completo y, al llegar, Los Altos resaltado con bordes y colores.

Misma idea que src/fondo.py: html(...) regresa una página que la app muestra con st.iframe. Los números los
calcula Python (tendencias por celda, contornos de INEGI, pluviómetros de CONAGUA) y viajan como JSON; aquí solo
se dibujan. Usa globe.gl (sobre three.js) por CDN con versión fija y la textura Blue Marble de NASA Visible Earth
(dominio público, reducida a 2048 × 1024 en static/tierra.jpg). Si la librería no carga o no hay WebGL, la página
muestra un aviso corto y la app sigue con la tabla de celdas.

Rendimiento: proporción de píxeles de 1.5 como máximo; el globo solo se dibuja mientras algo se mueve (se pausa
a los pocos segundos de quietud, fuera de la pantalla o con la pestaña oculta); con "reducir movimiento" no hay
giro ni vuelo. En pantallas táctiles no atrapa el dedo hasta tocar "Tap to explore".
"""

from __future__ import annotations

import html as html_lib
import json
import math
from functools import lru_cache

from src import estilo as E
from src import fondo, region

GLOBO_JS = "https://cdn.jsdelivr.net/npm/globe.gl@2.41.4/dist/globe.gl.min.js"
GLOBO_JS_LOCAL = "app/static/globe.gl-2.41.4.min.js"  # la misma versión, guardada en static/ (licencia MIT)
TEXTURA = "app/static/tierra.jpg"  # la sirve Streamlit (enableStaticServing en .streamlit/config.toml)
TEXTURA_RESPALDO = "https://cdn.jsdelivr.net/npm/three-globe@2.41.12/example/img/earth-blue-marble.jpg"
ALTO = 760           # px en escritorio (la CSS lo ajusta a la ventana); en el celular la CSS de src/estilo.py lo baja a ALTO_CELULAR
ALTO_CELULAR = E.ALTO_GLOBO_CELULAR
TOLERANCIA = 0.004   # grados (unos 400 m): los contornos de INEGI se simplifican para que la página pese poco
ALTITUD_MAXIMA = 0.0014  # nada de bloques: todo va pegado al suelo (en radios del planeta; 0.001 son 6 km)

_HTML = r"""<!doctype html><html lang="__IDIOMA__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;600&family=Outfit:wght@500&display=swap">
<style>
html,body{margin:0;height:100%;overflow:hidden;background:transparent;color:#F3F8FD;
  font-family:'Figtree','Segoe UI',Arial,Helvetica,sans-serif;font-size:14px}
#lienzo{position:absolute;inset:0;cursor:grab;opacity:0;transition:opacity .8s ease}
body.listo #lienzo{opacity:1}
#lienzo:active{cursor:grabbing}
body.bloqueado #lienzo{pointer-events:none}
.vidrio{background:rgba(9,34,66,.62);-webkit-backdrop-filter:blur(14px) saturate(150%);
  backdrop-filter:blur(14px) saturate(150%);border:1px solid rgba(255,255,255,.2);color:#F3F8FD}
#barra{position:absolute;left:12px;bottom:12px;display:flex;flex-wrap:wrap;gap:8px;max-width:calc(100% - 24px)}
button{font:inherit;font-weight:600;border-radius:999px;padding:8px 14px;cursor:pointer;line-height:1.2;
  transition:background .15s ease,transform .15s ease,box-shadow .15s ease}
button:hover{background:rgba(92,200,255,.26);transform:translateY(-1px);box-shadow:0 8px 18px -10px rgba(0,0,0,.7)}
button:focus-visible{outline:2px solid #5CC8FF;outline-offset:2px}
button.redondo{width:36px;padding:8px 0;text-align:center}
#explorar{position:absolute;right:12px;top:12px}
body.bloqueado #explorar{right:auto;top:auto;left:50%;bottom:64px;transform:translateX(-50%);padding:11px 20px;
  background:rgba(92,200,255,.3);border-color:rgba(255,255,255,.45);box-shadow:0 0 0 6px rgba(92,200,255,.12)}
#tarjeta{position:absolute;left:0;top:0;max-width:min(340px,calc(100% - 24px));border-radius:14px;padding:10px 12px;
  pointer-events:none;box-shadow:0 14px 30px -14px rgba(0,0,0,.75);z-index:5}
#tarjeta p{margin:0;line-height:1.4}
#tarjeta .l0{color:#B6CBE2;font-size:12.5px}
#tarjeta .l1{font-family:'Outfit','Segoe UI',Arial,sans-serif;font-weight:500;font-size:16px;margin:2px 0}
#tarjeta .l0:only-child{color:#F3F8FD;font-size:14px}
#tarjeta .segura{color:#FFFFFF;font-weight:600}
#tarjeta .extra{color:#B6CBE2;font-size:12.5px;margin-top:2px}
#tarjeta .titulo{font-family:'Outfit','Segoe UI',Arial,sans-serif;font-weight:500;font-size:17px;color:#FFD48A;
  margin:0 0 3px}
#tarjeta .pista{color:#5CC8FF;font-size:12px;margin-top:5px}
body.tactil #tarjeta{left:12px !important;top:12px !important;right:120px;max-width:none}
#aviso{position:absolute;inset:0;pointer-events:none;display:flex;align-items:center;justify-content:center;text-align:center;
  padding:24px;font-size:15px;line-height:1.5;color:#B6CBE2}
#creditos{position:absolute;right:12px;bottom:10px;margin:0;font-size:11px;color:rgba(243,248,253,.62);
  text-align:right;max-width:46%;pointer-events:none;text-shadow:0 1px 2px rgba(6,26,51,.9)}
.marca{width:0;height:0;pointer-events:none;visibility:hidden}
body.lejos .marca{visibility:visible;pointer-events:auto;cursor:pointer}
.marca span{position:absolute;left:20px;top:-17px;white-space:nowrap;font-weight:600;font-size:14px;color:#FFD48A;
  background:rgba(9,34,66,.72);border:1px solid rgba(255,212,138,.55);border-radius:12px;padding:5px 10px;
  box-shadow:0 0 22px -6px rgba(255,212,138,.8)}
.marca em{display:block;font-style:normal;font-weight:500;font-size:11.5px;color:#F3F8FD;letter-spacing:.02em}
.marca b{position:absolute;left:-7px;top:-7px;width:14px;height:14px;border-radius:50%;
  box-shadow:0 0 0 0 rgba(255,212,138,.55)}
.marca i{position:absolute;left:-7px;top:-7px;width:14px;height:14px;border-radius:50%;
  border:2px solid #FFD48A;box-sizing:border-box;box-shadow:0 0 0 0 rgba(255,212,138,.7)}
@media (prefers-reduced-motion: no-preference){.marca i{animation:pulso 1.8s ease-out infinite}
  .marca b{animation:pulso2 1.8s ease-out .9s infinite}}
@keyframes pulso{to{box-shadow:0 0 0 22px rgba(255,212,138,0)}}
@keyframes pulso2{to{box-shadow:0 0 0 38px rgba(255,212,138,0)}}
#arriba{position:absolute;left:12px;top:12px;display:flex;flex-direction:column;gap:8px;
  width:min(340px,calc(100% - 24px));z-index:4}
#buscador{font:inherit;border-radius:999px;padding:9px 15px;width:100%;box-sizing:border-box;outline:none}
#buscador::placeholder{color:#B6CBE2}
#buscador:focus{border-color:#5CC8FF;box-shadow:0 0 0 3px rgba(92,200,255,.28)}
#demo{margin:0;border-radius:12px;padding:7px 11px;font-size:12.5px;line-height:1.4;align-self:flex-start}
#demo b{color:#FFD48A;font-family:'Outfit','Segoe UI',Arial,sans-serif;letter-spacing:.08em;margin-right:6px}
#info{position:absolute;right:12px;top:12px;width:min(320px,calc(100% - 24px));border-radius:16px;padding:12px 14px;
  z-index:4;box-shadow:0 16px 34px -16px rgba(0,0,0,.8);border-color:rgba(255,212,138,.55)}
#info h3{margin:0 0 6px;font-family:'Outfit','Segoe UI',Arial,sans-serif;font-weight:500;font-size:19px;color:#FFD48A}
#info p{margin:0 0 3px;line-height:1.45;font-size:13.5px}
#info p.l0{color:#B6CBE2;font-size:12.5px}
#info button{margin-top:8px;padding:6px 12px;font-size:12.5px}
body.tactil #info{top:auto;bottom:64px}
@media (prefers-reduced-motion: no-preference){#info:not([hidden]){animation:entra .35s ease-out both}}
@keyframes entra{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}
[hidden]{display:none !important}
@media (max-width:520px){#creditos{display:none}#barra{gap:6px}button{padding:8px 11px;font-size:13px}
  #demo{display:none}}
</style></head><body>
<div id="lienzo"></div>
<div id="arriba"><input id="buscador" class="vidrio" list="lista" type="search" autocomplete="off"><datalist id="lista"></datalist><p id="demo" class="vidrio"></p></div>
<div id="info" class="vidrio" role="status" hidden></div>
<div id="tarjeta" class="vidrio" role="status" hidden></div>
<div id="aviso">__CARGANDO__</div>
<div id="barra">
  <button id="volver" class="vidrio" type="button"></button>
  <button id="planeta" class="vidrio" type="button"></button>
  <button id="acercar" class="vidrio redondo" type="button">+</button>
  <button id="alejar" class="vidrio redondo" type="button">&minus;</button>
</div>
<button id="explorar" class="vidrio" type="button" hidden></button>
<p id="creditos"></p>
<script>
(() => {
  const D = __DATOS__, T = D.textos, el = id => document.getElementById(id);
  el("volver").textContent = T.volver; el("planeta").textContent = T.planeta;
  el("acercar").setAttribute("aria-label", T.acercar); el("alejar").setAttribute("aria-label", T.alejar);
  el("creditos").textContent = T.creditos;
  el("buscador").placeholder = T.buscar; el("buscador").setAttribute("aria-label", T.buscar);
  { const b = document.createElement("b"); b.textContent = "DEMO"; el("demo").append(b, T.demo); }
  for (const m of D.municipios) { const o = document.createElement("option"); o.value = m.nombre; el("lista").append(o); }
  const sinGlobo = () => {
    el("aviso").textContent = T.sin_3d; el("aviso").hidden = false;
    for (const id of ["barra", "explorar", "creditos", "lienzo", "arriba", "info"]) el(id).hidden = true;
  };
  const hayWebGL = () => {
    try { const c = document.createElement("canvas"); return !!(c.getContext("webgl2") || c.getContext("webgl")); }
    catch (e) { return false; }
  };
  const inicia = () => {
  try {
    const quieto = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const tactil = matchMedia("(pointer: coarse)").matches || (navigator.maxTouchPoints > 0 && innerWidth < 760);
    const lienzo = el("lienzo");
    lienzo.setAttribute("role", "img"); lienzo.setAttribute("aria-label", T.aria);
    const rgba = (hex, a) => "rgba(" + [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)).join(",") + "," + a + ")";

    const globo = new Globe(lienzo, {rendererConfig: {antialias: true, alpha: true, powerPreference: "low-power"},
                                     animateIn: false, waitForGlobeReady: true});
    globo.renderer().setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    globo.width(innerWidth).height(innerHeight).backgroundColor("rgba(0,0,0,0)")
      .showGraticules(true).showAtmosphere(true).atmosphereColor(D.colores.agua).atmosphereAltitude(0.17);
    const ctl = globo.controls();
    window.ddGlobo = globo;  // para revisar el globo desde la consola del navegador (no lo usa la app)
    ctl.enableZoom = false;  // la rueda del mouse baja la página; para acercar están los botones + y −

    // --- Dibujar solo cuando hace falta ----------------------------------------------------
    let hasta = 0, visible = true, corriendo = true;
    const despierta = (ms = 1800) => {
      hasta = Math.max(hasta, performance.now() + ms);
      if (visible && !document.hidden && !corriendo) { globo.resumeAnimation(); corriendo = true; }
    };
    setInterval(() => {
      if (corriendo && (performance.now() > hasta || !visible || document.hidden)) {
        globo.pauseAnimation(); corriendo = false;
      }
    }, 300);
    new IntersectionObserver(es => { visible = es[es.length - 1].isIntersecting; if (visible) despierta(1200); })
      .observe(lienzo);
    document.addEventListener("visibilitychange", () => despierta(800));
    addEventListener("resize", () => { globo.width(innerWidth).height(innerHeight); despierta(800); });
    for (const ev of ["pointermove", "pointerdown", "touchstart", "wheel"])
      lienzo.addEventListener(ev, () => despierta(), {passive: true});
    lienzo.addEventListener("pointerdown", () => { ctl.autoRotate = false; });

    // --- Tierra: textura local ligera; si no está, la del CDN -------------------------------
    const imagen = new Image();
    imagen.crossOrigin = "anonymous";
    imagen.onload = () => { globo.globeImageUrl(imagen.src); despierta(1500); };
    imagen.onerror = () => {
      if (imagen.src.indexOf(D.textura_respaldo) === 0) return;
      imagen.src = D.textura_respaldo;
    };
    imagen.src = D.textura;

    // --- Municipios pintados con su dato; las celdas de POWER quedan como una cuadrícula tenue ------
    const ml = D.paso.lon / 2, mt = D.paso.lat / 2;
    const cuadro = (c, r) => [[c.lon - ml + r, c.lat - mt + r], [c.lon - ml + r, c.lat + mt - r],
                              [c.lon + ml - r, c.lat + mt - r], [c.lon + ml - r, c.lat - mt + r],
                              [c.lon - ml + r, c.lat - mt + r]];
    const horario = a => {  // la librería rellena el anillo en sentido horario; al revés pinta el planeta
      let area = 0;
      for (let i = 0; i < a.length - 1; i++) area += a[i][0] * a[i + 1][1] - a[i + 1][0] * a[i][1];
      return area > 0 ? a.slice().reverse() : a;
    };
    const piezas = [];
    D.municipios.forEach(m => m.anillos.forEach(a => piezas.push({m: m, geo: {type: "Polygon", coordinates: [horario(a)]}})));
    let encima = null, elegido = null, foco = 0, puntoEncima = null, celdaEncima = null, coords = null, raton = {x: 0, y: 0};
    const relleno = d => {  // el elegido se enciende y los demás se atenúan poco a poco (foco va de 0 a 1)
      const m = d.m;
      let a = (m.segura ? 0.66 : 0.52) + (m === encima ? 0.2 : 0);
      if (elegido) a = m === elegido ? a + 0.3 * foco : a * (1 - 0.6 * foco);
      return rgba(m.color, Math.min(a, 0.95));
    };
    globo.polygonsData(piezas).polygonGeoJsonGeometry("geo").polygonAltitude(0.0005).polygonCapColor(relleno)
      .polygonSideColor(() => "rgba(0,0,0,0)").polygonsTransitionDuration(0);

    const lineas = [];
    const trazo = (anillo, alt, color, ancho) =>  // ancho en píxeles; null = línea fina de 1 px
      lineas.push({pts: anillo.map(p => [p[1], p[0], alt]), color: color, ancho: ancho});
    D.celdas.forEach(c => trazo(cuadro(c, 0.01), 0.0006, c.segura ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.12)", null));
    // Las otras zonas con datos (si se eligió Altos Norte o Altos Sur) quedan marcadas, más tenues
    D.otros.forEach(m => m.anillos.forEach(a => trazo(a, 0.0006, "rgba(225,238,252,0.22)", null)));
    D.region.forEach(a => trazo(a, 0.0009, rgba(D.colores.zona, 0.45), 2));
    D.municipios.forEach(m => m.anillos.forEach(a => {
      if (m.segura) trazo(a, 0.0008, "rgba(255,255,255,0.22)", 7);  // tendencia segura: un brillo suave
      trazo(a, 0.0009, m.segura ? "rgba(255,255,255,0.92)" : "rgba(225,238,252,0.55)", m.segura ? 2 : null);
    }));
    D.zona.forEach(a => {
      trazo(a, 0.001, rgba(D.colores.zona, 0.3), 9);
      trazo(a, 0.0011, D.colores.zona, 3);
    });
    const base = lineas.slice();
    globo.pathsData(lineas).pathPoints("pts").pathPointLat(p => p[0]).pathPointLng(p => p[1])
      .pathPointAlt(p => p[2]).pathColor(d => d.color).pathStroke(d => d.ancho).pathTransitionDuration(0)
      .pathDashLength(d => d.dash || 1).pathDashGap(d => d.gap || 0).pathDashAnimateTime(d => d.anim || 0);
    const borde = (lista, m, alt, color, ancho, mas) => m.anillos.forEach(a =>
      lista.push(Object.assign({pts: a.map(p => [p[1], p[0], alt]), color: color, ancho: ancho}, mas || {})));
    const dibujaLineas = () => {  // base + el municipio bajo el cursor + el elegido (con una luz que recorre su borde)
      const extra = [];
      if (encima && encima !== elegido) borde(extra, encima, 0.0012, rgba(D.colores.zona, 0.95), 2.5);
      if (elegido) {
        borde(extra, elegido, 0.0012, rgba(D.colores.zona, 0.45), 14);
        borde(extra, elegido, 0.0013, "#FFFFFF", 3.5);
        if (!quieto) borde(extra, elegido, 0.0014, "rgba(255,255,255,0.95)", 6, {dash: 0.06, gap: 0.44, anim: 3200});
      }
      globo.pathsData(base.concat(extra));
    };

    // --- Pluviómetros de CONAGUA -----------------------------------------------------------
    globo.pointsData(D.estaciones).pointLat("lat").pointLng("lon").pointAltitude(0.0002).pointRadius(0.009)
      .pointColor(() => "#FFFFFF").pointResolution(10).pointsMerge(false).pointsTransitionDuration(0);

    // --- Marca de la región cuando se ve el planeta completo ---------------------------------
    const marca = document.createElement("div");
    marca.className = "marca";
    const nombre = document.createElement("span");
    nombre.textContent = T.lugar;
    const nota = document.createElement("em");
    nota.textContent = T.datos;
    nombre.append(nota);
    marca.append(document.createElement("i"), document.createElement("b"), nombre);
    globo.htmlElementsData([{lat: D.vista.lat, lng: D.vista.lng}]).htmlLat("lat").htmlLng("lng")
      .htmlAltitude(0.002).htmlElement(() => marca);
    const mideLejos = () => document.body.classList.toggle("lejos", globo.pointOfView().altitude > 0.55);
    ctl.addEventListener("change", mideLejos);

    // --- Tarjeta de vidrio al pasar el mouse o tocar -----------------------------------------
    const tarjeta = el("tarjeta");
    const dentro = (lon, lat, a) => {
      let d = false;
      for (let i = 0, j = a.length - 1; i < a.length; j = i++) {
        const xi = a[i][0], yi = a[i][1], xj = a[j][0], yj = a[j][1];
        if ((yi > lat) !== (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) d = !d;
      }
      return d;
    };
    const municipioObj = (lon, lat) => D.municipios.find(m => m.anillos.some(a => dentro(lon, lat, a))) || null;
    const municipioEn = (lon, lat) => { const m = municipioObj(lon, lat); return m ? m.nombre : null; };
    const coloca = () => {
      if (tactil) return;
      const w = tarjeta.offsetWidth, h = tarjeta.offsetHeight;
      tarjeta.style.left = Math.max(8, Math.min(raton.x + 16, innerWidth - w - 8)) + "px";
      tarjeta.style.top = Math.max(8, Math.min(raton.y + 16, innerHeight - h - 8)) + "px";
    };
    const pinta = () => {
      let titulo = null, textos = null, segura = false;
      if (puntoEncima) textos = puntoEncima.lineas;
      else if (encima) { titulo = encima.nombre; textos = encima.lineas; segura = encima.segura; }
      else if (celdaEncima) { textos = celdaEncima.lineas; segura = celdaEncima.segura; }
      if (!textos) { tarjeta.hidden = true; return; }
      const parrafos = [];
      if (titulo) { const h = document.createElement("p"); h.textContent = titulo; h.className = "titulo"; parrafos.push(h); }
      textos.forEach((texto, i) => {
        const p = document.createElement("p");
        p.textContent = texto;
        p.className = "l" + i + (i === textos.length - 1 && segura ? " segura" : "");
        parrafos.push(p);
      });
      if (titulo && encima !== elegido && !tactil) {
        const p = document.createElement("p"); p.textContent = T.clic; p.className = "pista"; parrafos.push(p);
      }
      tarjeta.replaceChildren(...parrafos);
      tarjeta.hidden = false;
      coloca();
    };
    const resalta = (m, c) => {
      const cambio = m !== encima;
      encima = m; celdaEncima = c;
      if (cambio) { globo.polygonCapColor(relleno); dibujaLineas(); }
      despierta(600);
    };
    // Qué hay bajo el cursor se calcula aquí (latitud y longitud del punto), sin los rayos de la librería:
    // las líneas finas de los municipios no estorban y funciona aunque el dibujo esté en pausa.
    const bajo = (x, y) => {
      const c = globo.toGlobeCoords(x, y);
      if (!c) return {c: null, punto: null, celda: null};
      const cerca = 9 * 53.4 * globo.pointOfView().altitude / Math.max(innerHeight, 1);  // unos 9 px, en grados
      const k = Math.cos(c.lat * Math.PI / 180);
      let punto = null, mejor = cerca;
      for (const e of D.estaciones) {
        const d = Math.hypot((e.lon - c.lng) * k, e.lat - c.lat);
        if (d < mejor) { mejor = d; punto = e; }
      }
      const celda = D.celdas.find(q => Math.abs(q.lat - c.lat) <= mt && Math.abs(q.lon - c.lng) <= ml) || null;
      return {c: c, punto: punto, celda: celda};
    };
    const senala = (x, y) => {
      const b = bajo(x, y);
      raton = {x: x, y: y}; coords = b.c; puntoEncima = b.punto;
      const m = b.c && !b.punto ? municipioObj(b.c.lng, b.c.lat) : null;
      resalta(m, m || b.punto ? null : b.celda);
      pinta();
      lienzo.style.cursor = (b.punto || m || b.celda) ? "pointer" : "";
    };
    const suelta = () => { puntoEncima = null; resalta(null, null); pinta(); lienzo.style.cursor = ""; };
    let abajo = null;
    lienzo.addEventListener("pointermove", e => { if (!tactil && !e.buttons) senala(e.clientX, e.clientY); }, {passive: true});
    lienzo.addEventListener("pointerleave", () => { if (!tactil) suelta(); });
    lienzo.addEventListener("pointerdown", e => {
      abajo = {x: e.clientX, y: e.clientY}; cancelAnimationFrame(animCam);  // si arrastra, la cámara le hace caso
      if (!tactil) tarjeta.hidden = true;
    });
    lienzo.addEventListener("pointerup", e => {  // un toque (sin arrastrar) muestra la tarjeta de esa celda
      if (abajo && Math.hypot(e.clientX - abajo.x, e.clientY - abajo.y) < 8) {
        senala(e.clientX, e.clientY);
        const c = globo.toGlobeCoords(e.clientX, e.clientY);
        const m = c && municipioObj(c.lng, c.lat);
        if (m && m !== elegido) elige(m);
      }
      abajo = null;
    });
    globo.enablePointerInteraction(false);

    // --- Cámara: planeta completo, vuelo a la zona y botones ---------------------------------
    const destino = () => {
      const aspecto = innerWidth / Math.max(innerHeight, 1);
      const ancho = D.vista.dlon * Math.cos(D.vista.lat * Math.PI / 180);
      const altitud = Math.max(D.vista.dlat, ancho / aspecto) * 1.18 / 53.4;  // 53.4° de alto por unidad de altitud
      return {lat: D.vista.lat, lng: D.vista.lng, altitude: Math.min(Math.max(altitud, 0.04), 0.4)};
    };
    let animCam = 0, animFoco = 0;
    const suave = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;  // arranca y frena suave
    const vuela = (vista, ms) => {
      ctl.autoRotate = false;
      cancelAnimationFrame(animCam);
      if (quieto || ms <= 0) { globo.pointOfView(vista, 0); despierta(1200); mideLejos(); return; }
      const ini = globo.pointOfView(), t0 = performance.now();
      let dl = vista.lng - ini.lng;
      if (dl > 180) dl -= 360;
      if (dl < -180) dl += 360;
      const lejos = Math.hypot(vista.lat - ini.lat, dl * Math.cos(vista.lat * Math.PI / 180));
      // Un pequeño salto: la cámara sube a mitad del camino y baja al llegar (más alto si el viaje es largo)
      const arco = Math.min(0.4, lejos / 40 + 0.5 * Math.min(ini.altitude, vista.altitude));
      despierta(ms + 1500);
      const paso = ahora => {
        const t = Math.min(1, (ahora - t0) / ms), e = suave(t);
        globo.pointOfView({lat: ini.lat + (vista.lat - ini.lat) * e, lng: ini.lng + dl * e,
                           altitude: ini.altitude + (vista.altitude - ini.altitude) * e + arco * Math.sin(Math.PI * t)}, 0);
        mideLejos();
        if (t < 1) animCam = requestAnimationFrame(paso);
      };
      animCam = requestAnimationFrame(paso);
    };
    // --- Elegir un municipio (buscador o clic): enfocarlo, iluminarlo y volar suave hasta él ---------
    const vistaDe = m => {
      const xs = m.anillos.flat().map(p => p[0]), ys = m.anillos.flat().map(p => p[1]);
      const lat = (Math.min(...ys) + Math.max(...ys)) / 2, lng = (Math.min(...xs) + Math.max(...xs)) / 2;
      const ancho = (Math.max(...xs) - Math.min(...xs)) * Math.cos(lat * Math.PI / 180);
      const alto = Math.max(...ys) - Math.min(...ys), aspecto = innerWidth / Math.max(innerHeight, 1);
      return {lat: lat, lng: lng, altitude: Math.min(Math.max(Math.max(alto, ancho / aspecto) * 3.1 / 53.4, 0.03), 0.3)};
    };
    const enfoca = () => {  // el relleno del elegido aparece en 0.8 s y los demás se atenúan
      cancelAnimationFrame(animFoco);
      if (quieto) { foco = 1; globo.polygonCapColor(relleno); return; }
      const t0 = performance.now();
      foco = 0;
      const paso = ahora => {
        foco = suave(Math.min(1, (ahora - t0) / 800));
        globo.polygonCapColor(relleno);
        if (foco < 1) animFoco = requestAnimationFrame(paso);
      };
      animFoco = requestAnimationFrame(paso);
    };
    const panel = () => {
      const info = el("info");
      if (!elegido) { info.hidden = true; return; }
      const h = document.createElement("h3"); h.textContent = elegido.nombre;
      const ps = elegido.lineas.map((t, i) => { const p = document.createElement("p"); p.textContent = t; p.className = "l" + i; return p; });
      const b = document.createElement("button"); b.type = "button"; b.className = "vidrio"; b.textContent = T.cerrar;
      b.onclick = () => { limpia(); vuela(destino(), 1700); };
      info.replaceChildren(h, ...ps, b); info.hidden = false;
    };
    const elige = m => {
      elegido = m; el("buscador").value = m.nombre;
      dibujaLineas(); enfoca(); panel();
      vuela(vistaDe(m), 1900);
      if (!quieto) despierta(Infinity);  // la luz que recorre el borde necesita seguir dibujando (se pausa fuera de vista)
    };
    const limpia = () => {
      elegido = null; foco = 0; el("buscador").value = "";
      cancelAnimationFrame(animFoco);
      dibujaLineas(); globo.polygonCapColor(relleno); panel();
      hasta = performance.now() + 1500;
    };
    const llave = t => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
    const busca = exacto => {
      const q = llave(el("buscador").value);
      if (!q) return;
      const m = D.municipios.find(x => llave(x.nombre) === q)
        || (!exacto && D.municipios.find(x => llave(x.nombre).includes(q)));
      if (m && m !== elegido) elige(m);
    };
    addEventListener("scroll", () => { if (scrollX || scrollY) scrollTo(0, 0); });  // la página del globo no se mueve
    el("buscador").addEventListener("change", () => busca(false));
    el("buscador").addEventListener("input", () => busca(true));
    el("buscador").addEventListener("keydown", e => { if (e.key === "Enter") busca(false); });
    marca.addEventListener("click", () => vuela(destino(), 2000));
    el("volver").onclick = () => { limpia(); vuela(destino(), 1700); };
    el("planeta").onclick = () => {
      limpia();
      vuela({lat: 12, lng: D.vista.lng, altitude: 1.55}, 1700);
      if (!quieto) setTimeout(() => { ctl.autoRotate = true; ctl.autoRotateSpeed = 0.5; despierta(20000); }, 1750);
    };
    const zoom = f => {
      const v = globo.pointOfView();
      vuela({lat: v.lat, lng: v.lng, altitude: Math.min(Math.max(v.altitude * f, 0.03), 3)}, 350);
    };
    el("acercar").onclick = () => zoom(0.66);
    el("alejar").onclick = () => zoom(1.5);

    // --- Celular: el dedo baja la página hasta tocar "Tap to explore" -------------------------
    let explorando = !tactil;
    const aplica = () => {
      document.body.classList.toggle("bloqueado", !explorando);
      document.body.classList.toggle("tactil", tactil);
      ctl.enabled = explorando;
      ctl.enableZoom = tactil && explorando;
      el("explorar").textContent = explorando ? T.terminar : T.explorar;
    };
    if (tactil) {
      el("explorar").hidden = false;
      el("explorar").onclick = () => {
        explorando = !explorando;
        if (!explorando) suelta();
        aplica(); despierta();
      };
    }
    aplica();

    // --- Relieve real de Los Altos sobre la textura (que de cerca se ve borrosa) --------------
    const relieve = () => {
      const R = D.relieve;
      if (!R) return true;
      let tierra = null;
      globo.scene().traverse(o => { if (!tierra && o.__globeObjType === "globe") tierra = o.isMesh ? o : o.children.find(h => h.isMesh); });
      if (!tierra) return false;  // la esfera todavía no existe: se reintenta
      const rad = Math.PI / 180, radio = tierra.geometry.parameters.radius;
      const geo = new tierra.geometry.constructor(radio * 1.0002, R.columnas - 1, R.filas - 1,
        (R.oeste + 180) * rad, (R.este - R.oeste) * rad, (90 - R.norte) * rad, (R.norte - R.sur) * rad);
      const H = R.alturas, n = R.filas * R.columnas, col = new Float32Array(n * 4);
      let min = Infinity, max = -Infinity;
      for (const fila of H) for (const m of fila) { if (m < min) min = m; if (m > max) max = m; }
      // Azules hondos (el relieve es contexto: los colores de las celdas van encima y deben resaltar)
      const tonos = [[0.006, 0.022, 0.055], [0.016, 0.055, 0.115], [0.040, 0.105, 0.190], [0.110, 0.200, 0.300]];
      const borde = 0.14;
      const alto = (i, j) => H[Math.max(0, Math.min(R.filas - 1, i))][Math.max(0, Math.min(R.columnas - 1, j))];
      for (let i = 0; i < R.filas; i++) for (let j = 0; j < R.columnas; j++) {
        const t = (H[i][j] - min) / Math.max(max - min, 1) * (tonos.length - 1);
        const k = Math.min(Math.floor(t), tonos.length - 2), f = t - k;
        const dx = alto(i, j + 2) + alto(i - 1, j + 2) + alto(i + 1, j + 2) - alto(i, j - 2) - alto(i - 1, j - 2) - alto(i + 1, j - 2);
        const dy = alto(i - 2, j) + alto(i - 2, j - 1) + alto(i - 2, j + 1) - alto(i + 2, j) - alto(i + 2, j - 1) - alto(i + 2, j + 1);
        const sombra = Math.max(0.5, Math.min(1.7, 1 + (dy - dx) / R.exagera));  // luz desde el noroeste
        const u = j / (R.columnas - 1), v = i / (R.filas - 1);
        const orilla = Math.min(u, 1 - u, v, 1 - v) / borde;
        const o = (i * R.columnas + j) * 4;
        for (let c = 0; c < 3; c++) col[o + c] = Math.min(1, (tonos[k][c] + (tonos[k + 1][c] - tonos[k][c]) * f) * sombra);
        col[o + 3] = 0.97 * Math.max(0, Math.min(1, orilla));  // se desvanece hacia la orilla
      }
      geo.setAttribute("color", new geo.attributes.position.constructor(col, 4));
      const material = new tierra.material.constructor({vertexColors: true, transparent: true, depthWrite: false,
                                                        shininess: 0});
      const malla = new tierra.constructor(geo, material);
      malla.rotation.copy(tierra.rotation);
      malla.renderOrder = -1;  // antes que las celdas, para que se vea a través de su relleno
      globo.scene().add(malla);
      // La textura, más fría y oscura alrededor: va con los azules de la app y no compite con los colores
      const fondoTierra = globo.globeMaterial();
      fondoTierra.color = new material.color.constructor(0x7f9fca);
      fondoTierra.needsUpdate = true;
      despierta(800);
      return true;
    };
    const ponRelieve = intentos => {
      try { if (!relieve() && intentos > 0) setTimeout(() => ponRelieve(intentos - 1), 250); }
      catch (e) { console.warn("Sin relieve en el globo:", e); }  // queda la textura
    };

    const entrada = () => {
      el("aviso").hidden = true;
      ponRelieve(40);
      document.body.classList.add("listo");
      let visto = false;
      try { visto = sessionStorage.getItem("dd-globo") === "1"; sessionStorage.setItem("dd-globo", "1"); } catch (e) {}
      const meta = destino();
      if (quieto) { globo.pointOfView(meta, 0); mideLejos(); despierta(2500); return; }
      if (visto) {  // ya vio la entrada: al cambiar zona, periodo o variable solo se acomoda
        globo.pointOfView({lat: meta.lat - 1.2, lng: meta.lng + 1.5, altitude: meta.altitude * 1.8}, 0);
        setTimeout(() => vuela(meta, 1300), 80);
        return;
      }
      globo.pointOfView({lat: 8, lng: meta.lng + 50, altitude: 1.55}, 0);
      mideLejos();
      ctl.autoRotate = true; ctl.autoRotateSpeed = 1.1;
      despierta(6000);
      setTimeout(() => vuela(meta, 2600), 2000);
    };
    despierta(6000);
    globo.onGlobeReady(entrada);
  } catch (e) { sinGlobo(); }
  };
  // La librería: en la compu (localhost) primero la copia local, que no depende del wifi; publicada, primero el
  // CDN (llega comprimida). Si una falla, se intenta la otra; si fallan las dos, queda el aviso y la tabla.
  if (!hayWebGL()) { sinGlobo(); return; }
  let enCasa = false;
  try { enCasa = ["localhost", "127.0.0.1", "[::1]"].includes(new URL(document.baseURI).hostname); } catch (e) {}
  const carga = fuentes => {
    if (!fuentes.length) { sinGlobo(); return; }
    const s = document.createElement("script");
    s.src = fuentes[0];
    s.onload = () => { if (window.Globe) inicia(); else carga(fuentes.slice(1)); };
    s.onerror = () => carga(fuentes.slice(1));
    document.head.appendChild(s);
  };
  carga(enCasa ? [D.libreria_local, D.libreria] : [D.libreria, D.libreria_local]);
})();
</script></body></html>"""


def _json(datos: dict) -> str:
    """JSON seguro para ir dentro de una etiqueta script: ningún texto puede cerrarla ni abrir otra."""
    texto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    for crudo, seguro in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), (" ", "\\u2028"),
                          (" ", "\\u2029")):
        texto = texto.replace(crudo, seguro)
    return texto


def simplificar(puntos: list, tolerancia: float = TOLERANCIA) -> list:
    """Douglas-Peucker: quita los puntos que se alejan menos de la tolerancia (grados) de la línea."""
    if len(puntos) < 3:
        return list(puntos)
    conservar = [False] * len(puntos)
    conservar[0] = conservar[-1] = True
    pila = [(0, len(puntos) - 1)]
    while pila:
        a, b = pila.pop()
        (xa, ya), (xb, yb) = puntos[a][:2], puntos[b][:2]
        dx, dy = xb - xa, yb - ya
        largo = math.hypot(dx, dy)
        lejos, cual = 0.0, None
        for i in range(a + 1, b):
            x, y = puntos[i][:2]
            d = abs(dy * (x - xa) - dx * (y - ya)) / largo if largo else math.hypot(x - xa, y - ya)
            if d > lejos:
                lejos, cual = d, i
        if cual is not None and lejos > tolerancia:
            conservar[cual] = True
            pila += [(a, cual), (cual, b)]
    return [p for p, c in zip(puntos, conservar) if c]


def _anillos(geometria: dict) -> list[list[list[float]]]:
    """Bordes exteriores de un Polygon o MultiPolygon, simplificados y con 4 decimales: [[lon, lat], ...]."""
    poligonos = [geometria["coordinates"]] if geometria["type"] == "Polygon" else geometria["coordinates"]
    anillos = []
    for poligono in poligonos:
        anillo = [[round(x, 4), round(y, 4)] for x, y in simplificar([p[:2] for p in poligono[0]])]
        if len(anillo) >= 4:
            anillos.append(anillo)
    return anillos


@lru_cache(maxsize=None)
def _contornos(id_zona: str) -> tuple[str, str]:
    """(zona, municipios) como JSON ya armado: son fijos para cada zona."""
    zona, municipios = [], []
    for rasgo in region.contorno(id_zona)["features"]:
        p = rasgo["properties"]
        if p["tipo"] == "zona":
            zona += _anillos(rasgo["geometry"])
        else:
            municipios.append({"nombre": p["nombre"], "anillos": _anillos(rasgo["geometry"])})
    return json.dumps(zona, separators=(",", ":")), json.dumps(municipios, ensure_ascii=False)


@lru_cache(maxsize=1)
def _relieve() -> str:
    """Relieve de data/region/relieve.json (alturas en metros enteros). 'null' si falta."""
    if not fondo.ARCHIVO_RELIEVE.exists():
        return "null"
    r = json.loads(fondo.ARCHIVO_RELIEVE.read_text(encoding="utf-8"))
    return json.dumps({"oeste": r["oeste"], "sur": r["sur"], "este": r["este"], "norte": r["norte"],
                       "filas": r["filas"], "columnas": r["columnas"], "exagera": 1100,
                       "alturas": [[round(m) for m in fila] for fila in r["alturas"]]}, separators=(",", ":"))


def encuadre(celdas: list[dict]) -> dict:
    """Centro y tamaño (grados) del recuadro que cubre las celdas: a dónde vuela la cámara."""
    norte = max(c["lat"] for c in celdas) + region.PASO_LAT / 2
    sur = min(c["lat"] for c in celdas) - region.PASO_LAT / 2
    este = max(c["lon"] for c in celdas) + region.PASO_LON / 2
    oeste = min(c["lon"] for c in celdas) - region.PASO_LON / 2
    return {"lat": round((norte + sur) / 2, 4), "lng": round((este + oeste) / 2, 4),
            "dlat": round(norte - sur, 4), "dlon": round(este - oeste, 4)}


def html(id_zona: str, celdas: list[dict], estaciones: list[dict], textos: dict, idioma: str = "en",
         municipios: dict[str, dict] | None = None) -> str:
    """Página del globo para la zona.

    celdas: [{lat, lon, color (#RRGGBB del relleno), segura (borde grueso y con brillo), lineas [textos de la
    tarjeta]}]. estaciones: [{lat, lon, lineas}]. textos: volver, planeta, explorar, terminar, acercar, alejar,
    sin_3d, cargando, creditos, municipio, lugar y aria. municipios: {nombre: {color, segura, lineas}} con el promedio
    de sus celdas (si falta uno, usa la celda sobre su centro). Todos los textos se escapan: viajan como JSON y se
    pintan con textContent, nunca como HTML.
    """
    if not celdas:
        raise ValueError("El globo necesita al menos una celda.")
    zona, municipios_json = _contornos(id_zona)
    region_json, todos_json = _contornos("los-altos")
    lista = json.loads(municipios_json)
    nombres = {m["nombre"] for m in lista}
    for m in lista:  # color y textos de cada municipio; sin datos propios, los de la celda sobre su centro
        propio = (municipios or {}).get(m["nombre"])
        if propio:
            m.update(color=str(propio["color"]), segura=bool(propio.get("segura")),
                     lineas=[str(t) for t in propio["lineas"]])
            continue
        puntos = [p for a in m["anillos"] for p in a]
        lon, lat = sum(p[0] for p in puntos) / len(puntos), sum(p[1] for p in puntos) / len(puntos)
        cerca = min(celdas, key=lambda c: (c["lon"] - lon) ** 2 + (c["lat"] - lat) ** 2)
        m.update(color=cerca["color"], segura=bool(cerca.get("segura")),
                 lineas=[str(textos.get("info", ""))] + [str(t) for t in cerca["lineas"][1:]])
    municipios = lista
    otros = [m for m in json.loads(todos_json) if m["nombre"] not in nombres]
    datos = {
        "zona": "__ZONA__", "municipios": municipios, "relieve": "__RELIEVE__",
        "otros": otros, "region": json.loads(region_json) if id_zona != "los-altos" else [],
        "celdas": [{"lat": c["lat"], "lon": c["lon"], "color": c["color"], "segura": bool(c.get("segura")),
                    "lineas": [str(t) for t in c["lineas"]]} for c in celdas],
        "estaciones": [{"lat": round(float(e["lat"]), 4), "lon": round(float(e["lon"]), 4),
                        "lineas": [str(t) for t in e["lineas"]]} for e in estaciones],
        "vista": encuadre(celdas),
        "paso": {"lat": region.PASO_LAT, "lon": region.PASO_LON},
        "colores": {"agua": E.AGUA, "zona": E.BORDE_ZONA},
        "textura": TEXTURA, "textura_respaldo": TEXTURA_RESPALDO,
        "libreria": GLOBO_JS, "libreria_local": GLOBO_JS_LOCAL,
        "textos": {k: str(v) for k, v in textos.items()},
    }
    cuerpo = _json(datos)
    # Lo fijo (contornos y relieve) ya es JSON de números y nombres de INEGI: se pega tal cual, también escapado
    for marca, valor in (('"__ZONA__"', zona), ('"__RELIEVE__"', _relieve())):
        cuerpo = cuerpo.replace(marca, valor, 1)
    return (_HTML.replace("__IDIOMA__", "es" if idioma == "es" else "en")
            .replace("__CARGANDO__", html_lib.escape(str(textos.get("cargando", ""))))
            .replace("__DATOS__", cuerpo))
