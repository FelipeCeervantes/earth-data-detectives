"""Identidad visual "Ventana al cielo": tokens, CSS (una sola inyección), plantilla de Plotly y piezas HTML.

La página es un cielo de temporal de lluvias sobre Los Altos: azul profundo arriba, más claro hacia el horizonte,
con nubes que se mueven despacio y, de fondo, el relieve real de la región en 3D (src/fondo.py). El contenido flota
en tarjetas de vidrio esmerilado con esquinas redondeadas, como una app del clima. Todo lo visual vive aquí;
app.py solo lo usa. No calcula nada.
Capas de tokens: primitivos (hex) → semánticos (para qué se usan) → componentes (veredicto, gráficas, mapa).
"""

from __future__ import annotations

import html
from string import Template

import plotly.graph_objects as go

from src import textos as T

# --- 1. Primitivos -------------------------------------------------------------------------
# Cielo (de arriba hacia el horizonte). El texto blanco pasa AA sobre todos (el más claro: 6.4:1).
CIELO_ALTO = "#061A33"
CIELO_HONDO = "#0B2B52"
CIELO = "#11437A"
HORIZONTE = "#1D63A3"
NUBE = "#F3F8FD"        # texto principal
NIEBLA = "#B6CBE2"      # texto secundario
TENUE = "#8FA9C6"       # ejes y notas
AGUA = "#5CC8FF"        # más agua · acento principal
SECO = "#FFB454"        # menos agua
DUDA = "#C3B5FF"        # todavía no se sabe
CALMA = "#A3B6CB"       # sin cambio
NEUTRO = "#DCE8F4"      # centro de la escala del mapa
BORDE_ZONA = "#FFD48A"  # contorno de la zona en el mapa y en el relieve
SEQUIA_BAJA = "#FFE7A3"  # pocos meses en sequía (escala secuencial del globo)
SEQUIA_ALTA = "#FF5C6C"  # muchos meses en sequía
ALTO_GLOBO_CELULAR = 420  # px; el mismo valor que src/globo.py (ALTO_CELULAR)

FUENTE_TITULOS = "Outfit"    # geométrica y amable: títulos y números grandes, como la temperatura de una app del clima
FUENTE_TEXTO = "Figtree"     # sans cálida y muy legible para todo lo que se lee
FUENTE_NUMEROS = FUENTE_TITULOS

# --- 2. Semánticos -------------------------------------------------------------------------
TINTA = NUBE
TINTA_SUAVE = NIEBLA
MAS_AGUA = AGUA
MENOS_AGUA = SECO
AMBAR = SECO
VIDRIO = "rgba(255,255,255,0.075)"
VIDRIO_FUERTE = "rgba(255,255,255,0.12)"
VIDRIO_BORDE = "rgba(255,255,255,0.16)"
PILA_TEXTO = f"'{FUENTE_TEXTO}', 'Segoe UI', Arial, Helvetica, sans-serif"
PILA_TITULOS = f"'{FUENTE_TITULOS}', 'Segoe UI', Arial, Helvetica, sans-serif"
PILA_NUMEROS = PILA_TITULOS

# --- 3. Componentes: veredicto -------------------------------------------------------------
# Las llaves son los colores que devuelve src.analisis.veredicto (no se cambian): "rojo" = sube, "verde" = baja.
# Aquí todo es agua, así que sube = más agua (azul) y baja = menos agua (naranja), igual que en el mapa.
# Ícono + palabra siempre, para no depender solo del color.
VEREDICTO = {
    "rojo": {"icono": "▲", "palabra": "Sube", "palabra_en": "Rising", "tinta": AGUA, "fondo": "rgba(92,200,255,0.14)"},
    "verde": {"icono": "▼", "palabra": "Baja", "palabra_en": "Falling", "tinta": SECO,
              "fondo": "rgba(255,180,84,0.14)"},
    "amarillo": {"icono": "?", "palabra": "No concluyente", "palabra_en": "Inconclusive", "tinta": DUDA,
                 "fondo": "rgba(195,181,255,0.14)"},
    "gris": {"icono": "=", "palabra": "Sin tendencia", "palabra_en": "No trend", "tinta": CALMA,
             "fondo": "rgba(163,182,203,0.12)"},
}

# Categorías de SPI y de estrés hídrico (niveles de src.indices.categoria). Ícono + nombre, nunca solo color.
NIVEL = {
    "humedo": {"color": AGUA, "icono": "▲"},
    "normal": {"color": "#6F89A8", "icono": "·"},
    "moderado": {"color": "#F7C948", "icono": "▼"},
    "severo": {"color": "#FF8C42", "icono": "▼▼"},
    "extremo": {"color": "#FF5C6C", "icono": "▼▼▼"},
    "sin-dato": {"color": "#3A5577", "icono": "–"},
}
# Bandas de fondo de las gráficas de índices: (desde, hasta, nivel, etiqueta corta)
BANDAS = [(-1.5, -1.0, "moderado", "moderada"), (-2.0, -1.5, "severo", "severa"), (-4.0, -2.0, "extremo", "extrema")]
# Monitor de Sequía de México: D0 (anormalmente seco) a D4 (excepcional)
MONITOR = {"D0": "#FFE7A3", "D1": "#F7C948", "D2": "#FF8C42", "D3": "#FF5C6C", "D4": "#E0569B"}


def palabra(color: str, idioma: str) -> str:
    """Palabra del veredicto ("Sube" / "Rising") para un color de src.analisis.veredicto."""
    return VEREDICTO[color]["palabra_en" if idioma == "en" else "palabra"]


def rgba(hex_color: str, alfa: float) -> str:
    r, g, b = rgb(hex_color)
    return f"rgba({r},{g},{b},{alfa})"


def rgb(hex_color: str) -> list[int]:
    return [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]


# --- CSS (una sola inyección) --------------------------------------------------------------
_CSS = Template("""
/* Ventana al cielo: lo que el tema nativo de Streamlit no cubre.
   Ojo: nada de etiquetas HTML ni signos de mayor o menor en esta CSS, o st.html descarta todo el bloque. */
:root {
  --dd-nube: $nube; --dd-niebla: $niebla; --dd-tenue: $tenue; --dd-agua: $agua; --dd-seco: $seco;
  --dd-vidrio: $vidrio; --dd-vidrio-fuerte: $vidrio_fuerte; --dd-vidrio-borde: $vidrio_borde;
  --dd-radio: 22px;
  --dd-sombra: 0 24px 48px -28px rgba(0,8,20,0.75), inset 0 1px 0 rgba(255,255,255,0.16);
  --dd-texto: $pila_texto; --dd-titulos: $pila_titulos;
}

/* El cielo: va en la raíz para que el relieve 3D (z-index -1) quede entre el cielo y el contenido */
html { background:
    radial-gradient(70vw 55vh at 88% -8%, rgba(92,200,255,0.26), rgba(92,200,255,0) 62%),
    radial-gradient(60vw 50vh at -5% 35%, rgba(29,99,163,0.50), rgba(29,99,163,0) 66%),
    linear-gradient(180deg, $alto 0%, $hondo 36%, $cielo 74%, $horizonte 100%) fixed;
  background-color: $hondo; }
body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"],
[data-testid="stBottomBlockContainer"] { background: transparent !important; }

/* Nubes que pasan despacio (solo si la persona no pidió menos movimiento) */
.stApp::before { content: ""; position: fixed; inset: -12% -25% auto -25%; height: 70vh; z-index: -2;
  pointer-events: none;
  background:
    radial-gradient(28vw 9vh at 18% 40%, rgba(255,255,255,0.10), rgba(255,255,255,0) 70%),
    radial-gradient(34vw 11vh at 58% 22%, rgba(255,255,255,0.08), rgba(255,255,255,0) 70%),
    radial-gradient(24vw 8vh at 86% 52%, rgba(255,255,255,0.07), rgba(255,255,255,0) 70%);
  filter: blur(6px); }
@keyframes dd-nubes { from { transform: translate3d(-5%, 0, 0); } to { transform: translate3d(5%, -2%, 0); } }
@media (prefers-reduced-motion: no-preference) { .stApp::before { animation: dd-nubes 80s ease-in-out infinite alternate; } }

/* Relieve 3D de fondo (src/fondo.py): ocupa toda la ventana, detrás de todo y sin atrapar el mouse */
.st-key-fondo3d { position: fixed !important; inset: 0; z-index: -1; pointer-events: none; }
.st-key-fondo3d iframe { position: fixed !important; inset: 0; width: 100vw !important; height: 100vh !important;
  border: 0; pointer-events: none; }

/* Sin barra de Streamlit encima del contenido (en el celular tapaba las tarjetas) */
[data-testid="stToolbar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stDecoration"] { display: none !important; }
[data-testid="stHeader"] { height: 0 !important; pointer-events: none; }
[data-testid="stMainBlockContainer"] { max-width: 1180px; padding-top: 1.6rem !important; padding-bottom: 3rem !important; }

/* Vidrio esmerilado */
.dd-significa, .dd-tarjeta, .dd-resumen, .dd-veredicto, [class*="st-key-evidencia"], .st-key-controles,
[data-testid="stPlotlyChart"], [data-testid="stDeckGlJsonChart"], [data-testid="stExpander"] details {
  background: var(--dd-vidrio) !important;
  -webkit-backdrop-filter: blur(18px) saturate(150%); backdrop-filter: blur(18px) saturate(150%);
  border: 1px solid var(--dd-vidrio-borde) !important; border-radius: var(--dd-radio) !important;
  box-shadow: var(--dd-sombra);
}
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .dd-significa, .dd-tarjeta, .dd-resumen, .dd-veredicto, [class*="st-key-evidencia"], .st-key-controles,
  [data-testid="stPlotlyChart"], [data-testid="stDeckGlJsonChart"], [data-testid="stExpander"] details {
    background: rgba(11,43,82,0.94) !important; }
}
[data-testid="stPlotlyChart"] { padding: .9rem .6rem .4rem; }
[data-testid="stDeckGlJsonChart"] { overflow: hidden; padding: 0; }
/* Sin mapa base: los bloques flotan sobre el vidrio, con los contornos y nombres de INEGI */
[data-testid="stDeckGlJsonChart"] .mapboxgl-canvas-container, [data-testid="stDeckGlJsonChart"] .mapboxgl-ctrl-attrib,
[data-testid="stDeckGlJsonChart"] .mapboxgl-ctrl-logo { visibility: hidden !important; }
[data-testid="stDeckGlJsonChart"] .mapboxgl-map { background: transparent !important; }
[data-testid="stDeckGlJsonChart"] .mapboxgl-ctrl-group { background: rgba(6,26,51,0.7) !important; border-radius: 12px !important; }
[data-testid="stDeckGlJsonChart"] .mapboxgl-ctrl-group button { filter: invert(1) hue-rotate(180deg); }
[class*="st-key-evidencia"] { padding: 1rem 1.1rem !important; }

/* Encabezado: la pregunta grande sobre el cielo */
.dd-hero { padding: .25rem 0 .2rem; }
p.dd-hero__marca { display: flex; align-items: center; gap: .55rem; font-family: var(--dd-titulos); font-weight: 600;
  font-size: .8rem !important; letter-spacing: .14em; text-transform: uppercase; color: var(--dd-agua);
  margin: 0 !important; }
p.dd-hero__marca::before { content: ""; width: .62rem; height: .62rem; border-radius: 50%; flex: none;
  background: radial-gradient(circle at 35% 35%, #FFFFFF, $agua 62%); box-shadow: 0 0 14px $agua; }
p.dd-hero__pregunta { font-family: var(--dd-titulos) !important; font-weight: 600; color: var(--dd-nube);
  font-size: clamp(2.1rem, 5.2vw, 3.9rem) !important; line-height: 1.02 !important; letter-spacing: -.025em;
  margin: .7rem 0 .55rem !important; max-width: 17ch; text-wrap: balance; }
p.dd-hero__numero { font-family: var(--dd-titulos); font-size: .86rem !important; color: var(--dd-niebla);
  letter-spacing: .03em; margin: 0 0 .35rem !important; }
p.dd-hero__nota { font-size: 1.05rem !important; color: var(--dd-niebla); max-width: 58ch; margin: 0 !important; }

/* Controles: zona y periodo en una tarjeta de vidrio */
.st-key-controles { padding: 1rem 1.25rem .6rem !important; margin-top: .4rem; }
[data-testid="stWidgetLabel"] p { font-family: var(--dd-titulos); font-weight: 600; font-size: .78rem !important;
  letter-spacing: .1em; text-transform: uppercase; color: var(--dd-niebla); }

/* Botones de opciones (zona, sección, capa, índice): píldoras de vidrio */
div[role="radiogroup"]:has(button[role="radio"]) { flex-wrap: wrap; gap: .4rem; }
button[role="radio"] { border-radius: 999px !important; margin: 0 !important;
  border: 1px solid var(--dd-vidrio-borde) !important; background: rgba(255,255,255,0.06) !important;
  color: var(--dd-niebla) !important; font-family: var(--dd-titulos); font-weight: 500; padding: .3rem .95rem !important;
  transition: background .15s ease, color .15s ease; }
button[role="radio"]:hover { background: rgba(255,255,255,0.14) !important; color: var(--dd-nube) !important; }
button[role="radio"][aria-checked="true"] { background: var(--dd-nube) !important; color: $hondo !important;
  border-color: var(--dd-nube) !important; box-shadow: 0 6px 18px -8px rgba(92,200,255,0.8); }
button[role="radio"][aria-checked="true"] * { color: $hondo !important; }

/* Navegación principal: tres secciones en una barra de vidrio que se queda arriba al bajar */
.st-key-vista { position: sticky; top: .6rem; z-index: 20; margin: .4rem 0 .2rem; }
.st-key-vista div[role="radiogroup"] { background: rgba(6,26,51,0.6); padding: .4rem; border-radius: 999px;
  -webkit-backdrop-filter: blur(18px) saturate(150%); backdrop-filter: blur(18px) saturate(150%);
  border: 1px solid var(--dd-vidrio-borde); box-shadow: var(--dd-sombra); flex-wrap: nowrap; width: 100%; }
.st-key-vista button[role="radio"] { flex: 1 1 0; border: 0 !important; background: transparent !important;
  font-size: 1.02rem; padding: .55rem .8rem !important; min-height: 2.9rem; }
.st-key-vista button[role="radio"][aria-checked="true"] { background: var(--dd-nube) !important; }

/* Títulos de sección: preguntas sencillas con una línea que se desvanece */
.dd-seccion { display: flex; align-items: center; gap: .9rem; margin: 1.8rem 0 .5rem; }
.dd-seccion::after { content: ""; flex: 1; height: 1px;
  background: linear-gradient(90deg, rgba(255,255,255,0.28), rgba(255,255,255,0)); }
p.dd-seccion__titulo { font-family: var(--dd-titulos) !important; font-weight: 600; color: var(--dd-nube);
  font-size: clamp(1.4rem, 2.8vw, 1.85rem) !important; line-height: 1.15 !important; margin: 0 !important;
  letter-spacing: -.01em; }

/* Veredicto: una insignia que brilla con el color de la dirección */
.dd-veredicto { display: flex; align-items: center; gap: 1rem 1.3rem; flex-wrap: wrap; margin: .9rem 0 .9rem;
  padding: .95rem 1.15rem; }
.dd-sello { display: inline-flex; align-items: center; gap: .5rem; border: 1.5px solid currentColor;
  border-radius: 999px; padding: .45rem 1.05rem; font-family: var(--dd-titulos); font-weight: 600; font-size: 1rem;
  letter-spacing: .05em; text-transform: uppercase; white-space: nowrap; max-width: 100%;
  box-shadow: 0 0 28px -8px currentColor; }
p.dd-veredicto__texto { flex: 1 1 20rem; font-size: 1.06rem !important; line-height: 1.55; color: var(--dd-nube); margin: 0 !important; }
@keyframes dd-aparecer { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: no-preference) { .dd-sello { animation: dd-aparecer 240ms ease-out both; } }
.dd-faltan { font-size: .98rem; color: var(--dd-niebla); border-left: 3px solid var(--dd-agua);
  padding: .1rem 0 .1rem .75rem; margin: 0 0 1rem; }

/* Evidencias: números grandes y ligeros, como la temperatura en una app del clima */
[data-testid="stHorizontalBlock"]:has([class*="st-key-evidencia"]) { align-items: stretch; }
[data-testid="stColumn"]:has([class*="st-key-evidencia"]) { align-self: stretch; }
[data-testid="stColumn"]:has([class*="st-key-evidencia"]) [data-testid="stVerticalBlock"],
[data-testid="stColumn"]:has([class*="st-key-evidencia"]) [data-testid="stLayoutWrapper"] { height: 100%; }
[data-testid="stMetricLabel"] p { font-family: var(--dd-titulos); font-size: .72rem !important; font-weight: 600;
  letter-spacing: .08em; text-transform: uppercase; color: var(--dd-niebla); }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { white-space: normal !important;
  overflow: visible !important; text-overflow: clip !important; }
[data-testid="stMetricValue"] { font-family: var(--dd-titulos); font-weight: 300; font-variant-numeric: tabular-nums;
  letter-spacing: -.02em; color: var(--dd-nube); font-size: clamp(1.6rem, 2.6vw, 2.3rem) !important;
  line-height: 1.12 !important; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { white-space: normal !important;
  overflow: visible !important; text-overflow: clip !important; }
[class*="st-key-evidencia"] [data-testid="stCaptionContainer"] p { font-size: .92rem; line-height: 1.45; color: var(--dd-niebla); }
[data-testid="stCaptionContainer"] p { color: var(--dd-niebla); }

/* "¿Qué significa?" debajo de cada gráfica */
.dd-significa { position: relative; padding: 1rem 1.25rem 1rem 1.5rem; margin: .5rem 0 1rem; overflow: hidden; }
.dd-significa::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: linear-gradient(180deg, $agua, $seco); }
p.dd-etiqueta { font-family: var(--dd-titulos); font-size: .72rem !important; font-weight: 600; letter-spacing: .1em;
  text-transform: uppercase; color: var(--dd-agua); margin: 0 0 .4rem !important; }
.dd-significa p.dd-significa__texto { font-size: 1.04rem !important; line-height: 1.6; margin: 0 !important; color: var(--dd-nube); }
.dd-significa p.dd-significa__no { font-size: .98rem !important; margin: .6rem 0 0 !important; color: var(--dd-niebla); }
.dd-limites { border-top: 1px solid rgba(255,255,255,0.12); margin-top: 1.6rem; padding-top: .8rem; }
.dd-limites p.dd-etiqueta { color: var(--dd-niebla); }
.dd-limites p { font-size: .92rem !important; color: var(--dd-niebla); margin: 0 0 .25rem !important; line-height: 1.5; }

/* Tarjetas del panorama */
.dd-tarjetas { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); gap: .9rem; margin: .4rem 0 1.1rem; }
.dd-tarjeta { position: relative; padding: 1.05rem 1.1rem 1rem; overflow: hidden; }
.dd-tarjeta::before { content: ""; position: absolute; left: 1.1rem; top: 0; width: 2.4rem; height: 3px;
  border-radius: 0 0 3px 3px; background: currentColor; box-shadow: 0 0 14px currentColor; }
.dd-tarjeta p { margin: 0 !important; }
.dd-tarjeta p.dd-etiqueta { color: var(--dd-niebla); margin-top: .35rem !important; }
.dd-tarjeta p.dd-tarjeta__valor { font-family: var(--dd-titulos); font-weight: 500; font-size: 1.35rem !important;
  line-height: 1.25; margin: .3rem 0 .45rem !important; }
.dd-tarjeta p.dd-tarjeta__texto { font-size: .96rem !important; line-height: 1.45; color: var(--dd-nube); }

/* Resumen en palabras sencillas */
.dd-resumen { padding: 1.3rem 1.5rem; }
.dd-resumen p.dd-resumen__titular { font-family: var(--dd-titulos); font-weight: 600;
  font-size: clamp(1.4rem, 2.8vw, 1.95rem) !important; line-height: 1.12 !important; margin: 0 0 .6rem !important;
  color: var(--dd-nube); letter-spacing: -.015em; }
.dd-resumen p, .dd-resumen li { font-size: 1.03rem !important; line-height: 1.6; color: var(--dd-nube); }
.dd-resumen ul { margin: .4rem 0 .8rem 1.1rem; padding: 0; }
.dd-resumen .dd-resumen__tema { font-family: var(--dd-titulos); font-weight: 600; font-size: .7rem; letter-spacing: .08em;
  text-transform: uppercase; color: var(--dd-agua); margin-right: .45rem; }
.dd-resumen p.dd-resumen__origen { font-size: .9rem !important; color: var(--dd-niebla); margin-top: .7rem !important; }

/* Municipio buscado en el mapa */
p.dd-buscado { background: var(--dd-vidrio-fuerte); border: 1px solid var(--dd-vidrio-borde); border-left: 4px solid #FFD48A;
  border-radius: 14px; padding: .7rem 1rem; margin: .7rem 0 .2rem !important; font-size: 1.02rem !important;
  color: var(--dd-nube); box-shadow: 0 0 24px -10px #FFD48A; }

/* Leyenda del mapa */
.dd-leyenda { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; font-size: .94rem; color: var(--dd-nube);
  margin: .55rem 0; }
.dd-leyenda__barra { width: 11rem; max-width: 45vw; height: .7rem; border-radius: 999px;
  background: linear-gradient(90deg, $seco, $neutro, $agua); box-shadow: 0 0 16px -4px rgba(92,200,255,0.6); }
.dd-leyenda__muestra { display: inline-block; width: 1.5rem; height: 1rem; border-radius: 5px; }
.dd-leyenda__muestra--segura { background: rgba(92,200,255,0.45); border: 3px solid #FFFFFF;
  box-shadow: 0 0 10px 1px rgba(255,255,255,0.7); }
.dd-leyenda__muestra--no { background: rgba(92,200,255,0.3); border: 1px solid rgba(255,255,255,0.55); }
.dd-leyenda__barra--sequia { background: linear-gradient(90deg, $sequia_baja, $sequia_alta);
  box-shadow: 0 0 16px -4px rgba(255,140,66,0.6); }

/* Señal invisible para la lluvia del fondo (src/fondo.py): no ocupa lugar */
[data-testid="stElementContainer"]:has(.dd-lluvia) { display: none; }

/* Globo 3D (src/globo.py): una ventana de vidrio grande, más ancha que el texto (hasta 1400 px) y casi del alto
   de la pantalla; en el celular es más bajo */
.st-key-globo { border-radius: var(--dd-radio); overflow: hidden; border: 1px solid var(--dd-vidrio-borde);
  background: radial-gradient(120% 90% at 50% 40%, rgba(17,67,122,0.55), rgba(6,26,51,0.82));
  box-shadow: var(--dd-sombra); width: min(calc(100vw - 2rem), 1400px) !important; max-width: none !important;
  position: relative; left: 50%; transform: translateX(-50%); }
/* El contenedor de Streamlit y el iframe miden lo mismo (si no, se corta la barra de botones de abajo) */
.st-key-globo [data-testid="stElementContainer"] { height: clamp(540px, 82vh, 860px) !important;
  flex: 0 0 auto !important; }
.st-key-globo iframe { display: block; border: 0; height: 100% !important; }

/* Tarjetas que responden: se levantan un poco al pasar el mouse (solo donde hay mouse) */
@media (hover: hover) and (prefers-reduced-motion: no-preference) {
  .dd-tarjeta, [class*="st-key-evidencia"], .dd-significa, .dd-resumen {
    transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
  .dd-tarjeta:hover, [class*="st-key-evidencia"]:hover, .dd-significa:hover, .dd-resumen:hover {
    transform: translateY(-3px); border-color: rgba(255,255,255,0.3) !important;
    box-shadow: 0 22px 44px -22px rgba(0,0,0,0.75), 0 0 0 1px rgba(92,200,255,0.12); }
}

/* Botones de descarga y expansores */
[data-testid="stDownloadButton"] button { border-radius: 999px !important; background: var(--dd-vidrio-fuerte) !important;
  border: 1px solid var(--dd-vidrio-borde) !important; }
[data-testid="stExpander"] details summary p { font-family: var(--dd-titulos); }

/* Pie: fuentes */
.dd-fuentes { border-top: 1px solid rgba(255,255,255,0.12); margin-top: 2rem; padding-top: 1rem;
  font-size: .92rem; color: var(--dd-niebla); line-height: 1.6; }
.dd-fuentes__titulo { font-family: var(--dd-titulos); font-size: .72rem; font-weight: 600; letter-spacing: .12em;
  text-transform: uppercase; color: var(--dd-nube); margin: 0 0 .35rem; }
.dd-fuentes a, .dd-significa a { color: var(--dd-agua); text-underline-offset: 3px; }

/* Foco visible con teclado */
:focus-visible { outline: 3px solid $agua !important; outline-offset: 2px; }

/* Pantallas angostas (375 px) */
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding-left: 1rem !important; padding-right: 1rem !important; }
  .st-key-controles { padding: .85rem .9rem .4rem !important; }
  .st-key-vista { top: .35rem; }
  .st-key-vista button[role="radio"] { font-size: .86rem; padding: .45rem .35rem !important; line-height: 1.15; }
  .st-key-vista button[role="radio"] * { white-space: normal !important; overflow: visible !important;
    text-overflow: clip !important; }
  .st-key-vista [data-testid="stIconMaterial"] { display: none; }
  .dd-sello { white-space: normal; font-size: .92rem; }
  [data-testid="stPlotlyChart"] { padding: .6rem .2rem .2rem; }
  /* El globo es más bajo en el celular (no atrapa el dedo: ver "Tap to explore" en src/globo.py) */
  .st-key-globo [data-testid="stElementContainer"] { height: ${alto_celular}px !important; flex: 0 0 auto !important; }
}
""")

CSS = "<style>" + _CSS.substitute(
    nube=NUBE, niebla=NIEBLA, tenue=TENUE, agua=AGUA, seco=SECO, neutro=NEUTRO, alto=CIELO_ALTO, hondo=CIELO_HONDO,
    cielo=CIELO, horizonte=HORIZONTE, vidrio=VIDRIO, vidrio_fuerte=VIDRIO_FUERTE, vidrio_borde=VIDRIO_BORDE,
    pila_texto=PILA_TEXTO, pila_titulos=PILA_TITULOS, sequia_baja=SEQUIA_BAJA, sequia_alta=SEQUIA_ALTA,
    alto_celular=ALTO_GLOBO_CELULAR,
) + "</style>"

# --- Plantilla de Plotly -------------------------------------------------------------------
# Ejes fijos y sin arrastre: en el celular, deslizar el dedo baja la página en vez de hacer zoom.
_EJE = dict(gridcolor="rgba(255,255,255,0.08)", griddash="dot", gridwidth=1, linecolor="rgba(255,255,255,0.16)",
            zerolinecolor="rgba(255,255,255,0.35)", fixedrange=True, automargin=True,
            tickfont=dict(family=PILA_NUMEROS, size=12, color=NIEBLA),
            title=dict(font=dict(family=PILA_TEXTO, size=13, color=NIEBLA)))
PLANTILLA = go.layout.Template(layout=dict(
    font=dict(family=PILA_TEXTO, size=14, color=NUBE),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=_EJE, yaxis=_EJE, dragmode=False,
    margin=dict(t=12, b=8, l=8, r=8),
    hoverlabel=dict(bgcolor="rgba(6,26,51,0.94)", bordercolor="rgba(255,255,255,0.25)",
                    font=dict(family=PILA_TEXTO, size=13, color=NUBE)),
    # Leyenda abajo y en fila: en el celular ya no tapa la gráfica
    legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, xanchor="left",
                font=dict(family=PILA_TEXTO, size=13, color=NIEBLA), bgcolor="rgba(0,0,0,0)"),
    separators=".,",
))
SERIE_MENSUAL = dict(color=rgba(NIEBLA, 0.5), width=1)
FORMATO_MES = "%b %Y"  # encabezado del recuadro al pasar el mouse: "mar 1998" / "Mar 1998"


def config_grafica(idioma: str) -> dict:
    """Sin barra de herramientas ni zoom (en el celular se encimaba y atrapaba el dedo) y fechas en el idioma."""
    base = {"displaylogo": False, "displayModeBar": False, "scrollZoom": False, "doubleClick": False,
            "responsive": True}
    if idioma == "en":
        return base  # Plotly ya viene en inglés
    meses, dias = T.MESES["es"], T.DIAS["es"]
    return {**base, "locale": "es-dd", "locales": {"es-dd": {"format": {
        "months": meses, "shortMonths": [m[:3] for m in meses], "days": dias, "shortDays": [d[:3] for d in dias],
        "decimal": ".", "thousands": ",",
    }}}}


def _mezcla(a: str, b: str, t: float) -> str:
    ca, cb = rgb(a), rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def color_cambio(valor: float, maximo: float) -> str:
    """Escala divergente del mapa: naranja = hacia menos agua, casi blanco = sin cambio, azul = hacia más agua."""
    if valor is None or maximo <= 0 or valor != valor:  # NaN
        return CALMA
    t = max(-1.0, min(1.0, valor / maximo))
    # Raíz cuadrada: los cambios chicos ya se distinguen del "sin cambio" (con escala lineal salían grises)
    return _mezcla(NEUTRO, MAS_AGUA if t > 0 else MENOS_AGUA, abs(t) ** 0.5)


def color_sequia(valor: float, minimo: float, maximo: float) -> str:
    """Escala secuencial del globo: amarillo = pocos meses en sequía, rojo = muchos (entre el mínimo y el máximo)."""
    if valor is None or valor != valor:  # NaN
        return CALMA
    t = 0.5 if maximo <= minimo else max(0.0, min(1.0, (valor - minimo) / (maximo - minimo)))
    return _mezcla(SEQUIA_BAJA, SEQUIA_ALTA, t)


# --- Piezas HTML ---------------------------------------------------------------------------
def hero_html(numero: str, pregunta: str, nota: str, idioma: str = "es") -> str:
    """Encabezado: marca, la pregunta grande y cómo usar la página."""
    return (f'<div class="dd-hero"><p class="dd-hero__marca">{T.t("marca.nombre", idioma)} · '
            f'{T.t("marca.lema", idioma)}</p>'
            f'<p class="dd-hero__pregunta" role="heading" aria-level="1">{html.escape(pregunta)}</p>'
            f'<p class="dd-hero__numero">{T.t("caso.prefijo", idioma)} {html.escape(numero)}</p>'
            f'<p class="dd-hero__nota">{html.escape(nota)}</p></div>')


def buscado_html(texto: str) -> str:
    """Lo que dice el mapa del municipio buscado, en una tarjeta de vidrio con borde ámbar."""
    return f'<p class="dd-buscado">{html.escape(texto)}</p>'


def seccion_html(titulo: str) -> str:
    return f'<div class="dd-seccion"><p class="dd-seccion__titulo" role="heading" aria-level="2">{html.escape(titulo)}</p></div>'


def sello_html(color: str, texto: str, idioma: str = "es") -> str:
    """Veredicto como insignia: ícono + VEREDICTO: PALABRA, y la explicación al lado."""
    v = VEREDICTO[color]
    return (f'<div class="dd-veredicto"><div class="dd-sello" style="color:{v["tinta"]};background:{v["fondo"]}">'
            f'<span class="dd-sello__icono" aria-hidden="true">{v["icono"]}</span>{T.t("sello.veredicto", idioma)}: '
            f'{palabra(color, idioma)}</div><p class="dd-veredicto__texto">{html.escape(texto)}</p></div>')


def faltan_html(anios: int, idioma: str = "es") -> str:
    return f'<p class="dd-faltan">{T.t("faltan", idioma, n=anios)}</p>'


def fuentes_html(creditos_html: str, idioma: str = "es") -> str:
    return (f'<div class="dd-fuentes"><p class="dd-fuentes__titulo">{T.t("etq.fuentes", idioma)}</p>'
            f'{creditos_html}</div>')


def significa_html(texto: str, no_es: str | None = None, idioma: str = "es") -> str:
    """Recuadro "¿Qué significa?" con su "Qué no es" opcional."""
    extra = (f'<p class="dd-significa__no"><strong>{T.t("etq.que_no_es", idioma)}</strong> {html.escape(no_es)}</p>'
             if no_es else "")
    return (f'<div class="dd-significa"><p class="dd-etiqueta">{T.t("etq.que_significa", idioma)}</p>'
            f'<p class="dd-significa__texto">{html.escape(texto)}</p>{extra}</div>')


def limites_html(partes: list[str], idioma: str = "es") -> str:
    """"Fuente y limitaciones" al final de una sección: un párrafo por fuente o límite."""
    return (f'<div class="dd-limites"><p class="dd-etiqueta">{T.t("etq.fuente_limites", idioma)}</p>'
            + "".join(f"<p>{html.escape(p)}</p>" for p in dict.fromkeys(partes)) + "</div>")


def tarjetas_html(tarjetas: list[dict]) -> str:
    """Tarjetas del panorama: [{tema, icono, valor, texto, color}]. Ícono + palabras, no solo color."""
    partes = []
    for t in tarjetas:
        partes.append(
            f'<div class="dd-tarjeta" style="color:{t["color"]}"><p class="dd-etiqueta">{html.escape(t["tema"])}</p>'
            f'<p class="dd-tarjeta__valor"><span aria-hidden="true">{t["icono"]}</span> {html.escape(t["valor"])}</p>'
            f'<p class="dd-tarjeta__texto">{html.escape(t["texto"])}</p></div>')
    return f'<div class="dd-tarjetas">{"".join(partes)}</div>'


def resumen_html(res: dict, origen: str, idioma: str = "es") -> str:
    """Resumen en palabras (formato de src.explicar). Todo el texto se escapa: puede venir de Gemini."""
    e = html.escape
    puntos = "".join(
        f'<li><span class="dd-resumen__tema">{T.t("tema." + p["tema"], idioma) if T.tiene("tema." + str(p.get("tema")), idioma) else ""}'
        f'</span>{e(p.get("texto", ""))}</li>' for p in res.get("puntos", []))
    cuidado = "".join(f"<li>{e(c)}</li>" for c in res.get("cuidado", []))
    pensar = (f'<p><strong>{T.t("etq.para_pensar", idioma)}</strong> {e(res["para_pensar"])}</p>'
              if res.get("para_pensar") else "")
    return (f'<div class="dd-resumen"><p class="dd-etiqueta">{T.t("etq.resumen", idioma)}</p>'
            f'<p class="dd-resumen__titular" role="heading" aria-level="3">{e(res.get("titular", ""))}</p>'
            f'<p>{e(res.get("resumen", ""))}</p><ul>{puntos}</ul>'
            + (f'<p class="dd-etiqueta">{T.t("etq.cuidado", idioma)}</p><ul>{cuidado}</ul>' if cuidado else "")
            + f'{pensar}<p class="dd-resumen__origen">{e(origen)}</p></div>')


def leyenda_mapa_html(maximo: float, unidades: str, seguras: int, total: int, idioma: str = "es") -> str:
    """Escala de color y cómo se ve una tendencia segura (las dos pruebas coinciden)."""
    return (f'<div class="dd-leyenda"><span><span aria-hidden="true">▼</span> {T.t("leyenda.menos", idioma)} '
            f'(−{maximo:.2f} {html.escape(unidades)} {T.t("leyenda.por_decada", idioma)})</span>'
            f'<span class="dd-leyenda__barra" aria-hidden="true"></span><span><span aria-hidden="true">▲</span> '
            f'{T.t("leyenda.mas", idioma)} (+{maximo:.2f})</span></div>'
            f'<div class="dd-leyenda"><span class="dd-leyenda__muestra dd-leyenda__muestra--segura" aria-hidden="true">'
            f'</span><span>{T.t("leyenda.segura", idioma)}</span><span class="dd-leyenda__muestra '
            f'dd-leyenda__muestra--no" aria-hidden="true"></span><span>{T.t("leyenda.no_segura", idioma)}</span>'
            f'<strong>{T.t("leyenda.cuenta", idioma, n=seguras, total=total)}</strong></div>')


def leyenda_sequia_html(minimo: int, maximo: int, idioma: str = "es") -> str:
    """Escala de color del globo cuando muestra los meses en sequía de cada celda."""
    return (f'<div class="dd-leyenda"><span>{T.t("leyenda.sequia_menos", idioma, n=minimo)}</span>'
            f'<span class="dd-leyenda__barra dd-leyenda__barra--sequia" aria-hidden="true"></span>'
            f'<span>{T.t("leyenda.sequia_mas", idioma, n=maximo)}</span></div>'
            f'<div class="dd-leyenda"><span>{T.t("leyenda.sequia_nota", idioma)}</span></div>')
