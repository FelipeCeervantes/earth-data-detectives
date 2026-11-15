"""Identidad visual "Cielo sobre tierra seca": tokens, CSS (una sola inyección), plantilla de Plotly y piezas HTML.

El fondo es la atmósfera de Los Altos: cielo de lluvia arriba, tierra seca (con grietas tenues) abajo, nubes
y calor difuminados; el contenido flota en paneles de vidrio esmerilado. Todo lo visual vive aquí; app.py
solo lo usa. No calcula nada.
Capas de tokens: primitivos (hex) → semánticos (para qué se usan) → componentes (veredicto, gráfica).
"""

from __future__ import annotations

import html
from string import Template
from urllib.parse import quote

import plotly.graph_objects as go

from src import textos as T

# --- 1. Primitivos -------------------------------------------------------------------------
# Contraste AA comprobado: noche y tinta suave sobre vidrio, bruma y polvo; ámbar y niebla sobre la barra nocturna.
NOCHE = "#14212B"       # tinta del texto y cielo nocturno de la barra lateral
NOCHE_2 = "#1F3443"     # final del degradado de la barra lateral
BRUMA = "#D6E2E7"       # cielo húmedo, arriba
NIEBLA = "#EEF2F1"      # transición, y "sin cambio" en el mapa
POLVO = "#EAD7C0"       # tierra seca, abajo
LLUVIA = "#2B6A86"      # más agua
TIERRA = "#A3401F"      # menos agua: tierra colorada de Los Altos
AMBAR = "#E2A24A"       # calor: detalles, foco y etiquetas sobre la barra (nunca texto sobre claro)
GRIETA = "#8E5E3C"      # textura de suelo agrietado

PAPEL = NIEBLA          # (nombre heredado) neutro de las escalas
TARJETA = "#FBFCFC"
TINTA = NOCHE
TINTA_SUAVE = "#465560"
LINEA = "#C9D3D6"
SENAL = AMBAR
TINTA_PANEL = "#263C4C"  # campos dentro de la barra lateral

FUENTE_TITULOS = "Bricolage Grotesque"          # robusta y terrosa, en ancho condensado: letrero de campo
FUENTE_TEXTO = "Atkinson Hyperlegible Next"     # hecha para que la lea cualquiera
FUENTE_NUMEROS = "Martian Mono"                 # lectura de instrumento de estación meteorológica

# --- 2. Semánticos -------------------------------------------------------------------------
FONDO = NIEBLA
SUPERFICIE = TARJETA
TEXTO = TINTA
TEXTO_SECUNDARIO = TINTA_SUAVE
BORDE = LINEA
FOCO = SENAL
VIDRIO = "rgba(255,255,255,0.64)"
VIDRIO_BORDE = "rgba(255,255,255,0.78)"
PILA_TEXTO = f"'{FUENTE_TEXTO}', 'Atkinson Hyperlegible', 'Segoe UI', system-ui, sans-serif"
PILA_TITULOS = f"'{FUENTE_TITULOS}', 'Segoe UI', system-ui, sans-serif"
PILA_NUMEROS = f"'{FUENTE_NUMEROS}', ui-monospace, Consolas, monospace"

# --- 3. Componentes: veredicto -------------------------------------------------------------
# Las llaves son los colores que devuelve src.analisis.veredicto (no se cambian).
# "verde" (baja) se muestra azul petróleo: el color marca la dirección, no si es bueno o malo.
# Ícono + palabra siempre, para no depender solo del color.
VEREDICTO = {
    "rojo": {"icono": "▲", "palabra": "Sube", "palabra_en": "Rising", "tinta": "#A83F1B", "fondo": "#F6DED3"},
    "verde": {"icono": "▼", "palabra": "Baja", "palabra_en": "Falling", "tinta": "#1F6F8B", "fondo": "#D8EBF1"},
    "amarillo": {"icono": "?", "palabra": "No concluyente", "palabra_en": "Inconclusive", "tinta": "#8A5A00",
                 "fondo": "#F7EBC9"},
    "gris": {"icono": "=", "palabra": "Sin tendencia", "palabra_en": "No trend", "tinta": "#5B6472", "fondo": "#E9E6DF"},
}


# Categorías de SPI y de estrés hídrico (niveles de src.indices.categoria). Ícono + nombre, nunca solo color.
NIVEL = {
    "humedo": {"color": "#1F6F8B", "icono": "▲"},
    "normal": {"color": "#8C939D", "icono": "·"},
    "moderado": {"color": "#B9832A", "icono": "▼"},
    "severo": {"color": "#A83F1B", "icono": "▼▼"},
    "extremo": {"color": "#6E2412", "icono": "▼▼▼"},
    "sin-dato": {"color": "#D9CFBD", "icono": "–"},
}
# Bandas de fondo de las gráficas de índices: (desde, hasta, nivel, etiqueta corta)
BANDAS = [(-1.5, -1.0, "moderado", "moderada"), (-2.0, -1.5, "severo", "severa"), (-4.0, -2.0, "extremo", "extrema")]
MENOS_AGUA = TIERRA   # tierra colorada
MAS_AGUA = LLUVIA     # azul de lluvia


def palabra(color: str, idioma: str) -> str:
    """Palabra del veredicto ("Sube" / "Rising") para un color de src.analisis.veredicto."""
    return VEREDICTO[color]["palabra_en" if idioma == "en" else "palabra"]


def rgba(hex_color: str, alfa: float) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alfa})"


# --- Texturas (SVG dentro del CSS) ---------------------------------------------------------
# Isobaras: las líneas de presión de un mapa del tiempo, en el encabezado del caso.
_ISOBARAS_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='640' height='260' viewBox='0 0 640 260'>"
    f"<g fill='none' stroke='{LLUVIA}' stroke-width='1.2' stroke-opacity='0.28'>"
    "<path d='M-10 210 C 90 170 170 240 280 200 S 470 130 650 180'/>"
    "<path d='M-10 180 C 100 140 180 205 290 168 S 460 100 650 150'/>"
    "<path d='M-10 150 C 110 112 190 172 300 138 S 450 72 650 120'/>"
    "<path d='M-10 240 C 80 205 160 262 270 230 S 480 165 650 212'/>"
    "<path d='M470 40 C 520 18 590 30 600 62 S 560 118 505 108 S 430 70 470 40 Z'/>"
    "<path d='M492 52 C 525 38 572 46 578 66 S 552 98 515 92 S 468 70 492 52 Z'/>"
    "<path d='M512 62 C 530 55 556 59 559 70 S 545 84 525 81 S 500 70 512 62 Z'/>"
    "<path d='M-10 110 C 60 90 120 120 190 98 S 300 40 390 60'/>"
    "</g></svg>"
)
CURVAS_URL = "data:image/svg+xml;utf8," + quote(_ISOBARAS_SVG)

# Suelo agrietado: un mosaico que se repite sin costuras (los bordes coinciden); solo se ve abajo del fondo.
_GRIETAS_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240' viewBox='0 0 240 240'>"
    f"<g fill='none' stroke='{GRIETA}' stroke-width='1.1' stroke-linecap='round' stroke-linejoin='round' "
    "stroke-opacity='0.42'>"
    "<path d='M0 40 L38 52 L61 30 L102 46 L131 20 L170 38 L204 26 L240 40'/>"
    "<path d='M61 30 L70 0'/><path d='M131 20 L138 0'/>"
    "<path d='M38 52 L30 96 L52 128 L40 170 L60 204 L70 240'/>"
    "<path d='M102 46 L96 88 L128 112 L120 150 L150 176 L142 214 L138 240'/>"
    "<path d='M170 38 L176 80 L210 100 L240 96'/><path d='M0 96 L30 96'/>"
    "<path d='M176 80 L150 104 L128 112'/>"
    "<path d='M0 152 L22 146 L52 128 L84 138 L120 150'/>"
    "<path d='M210 100 L216 140 L240 152'/><path d='M216 140 L190 168 L150 176'/>"
    "<path d='M0 214 L28 200 L60 204 L96 222 L142 214 L190 228 L240 214'/>"
    "<path d='M190 168 L198 200 L190 228'/>"
    "</g></svg>"
)
GRIETAS_URL = "data:image/svg+xml;utf8," + quote(_GRIETAS_SVG)

# --- CSS (una sola inyección) --------------------------------------------------------------
_CSS = Template("""
/* Cielo sobre tierra seca: lo que el tema nativo de Streamlit no cubre.
   Ojo: nada de etiquetas HTML ni signos de mayor o menor en esta CSS, o st.html descarta todo el bloque. */
:root {
  --dd-papel: $papel; --dd-tarjeta: $tarjeta; --dd-tinta: $tinta; --dd-tinta-suave: $tinta_suave;
  --dd-linea: $linea; --dd-senal: $senal; --dd-lluvia: $lluvia; --dd-tierra: $tierra;
  --dd-vidrio: $vidrio; --dd-vidrio-borde: $vidrio_borde;
  --dd-sombra: 0 12px 32px -16px rgba(20,33,43,0.32), inset 0 1px 0 rgba(255,255,255,0.85);
  --dd-texto: $pila_texto; --dd-titulos: $pila_titulos; --dd-numeros: $pila_numeros;
}

/* La atmósfera: nubes y calor difuminados sobre un cielo de lluvia que baja hasta tierra seca agrietada */
.stApp {
  background-color: $niebla !important;
  background-image:
    radial-gradient(62vw 42vh at 10% 6%, rgba(255,255,255,0.80), rgba(255,255,255,0) 70%),
    radial-gradient(52vw 36vh at 80% 12%, rgba(43,106,134,0.20), rgba(43,106,134,0) 70%),
    radial-gradient(40vw 26vh at 46% 30%, rgba(255,255,255,0.55), rgba(255,255,255,0) 70%),
    radial-gradient(58vw 42vh at 90% 94%, rgba(226,162,74,0.30), rgba(226,162,74,0) 70%),
    radial-gradient(46vw 32vh at 14% 98%, rgba(163,64,31,0.14), rgba(163,64,31,0) 70%),
    linear-gradient(180deg, $bruma 0%, $niebla 40%, rgba(238,242,241,0) 74%),
    url("$grietas"),
    linear-gradient(180deg, $bruma 0%, $niebla 46%, $polvo 100%) !important;
  background-size: auto, auto, auto, auto, auto, auto, 240px 240px, auto !important;
  background-attachment: fixed !important;
}
[data-testid="stHeader"], [data-testid="stBottomBlockContainer"] { background: transparent !important; }
html, body { background: $polvo; }

/* Vidrio esmerilado: los paneles flotan sobre el cielo */
.dd-caso, .dd-significa, .dd-tarjeta, .dd-resumen, [class*="st-key-evidencia"],
[data-testid="stPlotlyChart"], [data-testid="stIFrame"], [data-testid="stExpander"] details {
  background: var(--dd-vidrio) !important;
  -webkit-backdrop-filter: blur(16px) saturate(140%); backdrop-filter: blur(16px) saturate(140%);
  border: 1px solid var(--dd-vidrio-borde) !important; border-radius: 14px !important;
  box-shadow: var(--dd-sombra);
}
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .dd-caso, .dd-significa, .dd-tarjeta, .dd-resumen, [class*="st-key-evidencia"],
  [data-testid="stPlotlyChart"], [data-testid="stIFrame"], [data-testid="stExpander"] details {
    background: rgba(255,255,255,0.92) !important; }
}
[data-testid="stPlotlyChart"] { padding: .6rem .4rem .2rem; }
[data-testid="stIFrame"] { padding: 4px; overflow: hidden; }

/* Barra lateral: cielo nocturno, con la humedad arriba y el calor que sube desde abajo */
section[data-testid="stSidebar"] {
  background:
    radial-gradient(120% 55% at 15% 0%, rgba(43,106,134,0.55), rgba(43,106,134,0) 62%),
    radial-gradient(120% 45% at 85% 100%, rgba(226,162,74,0.30), rgba(226,162,74,0) 62%),
    linear-gradient(180deg, $noche 0%, $noche_2 100%) !important;
  border-right: 1px solid rgba(255,255,255,0.08);
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] { background: transparent !important; }

/* Marca superior */
.dd-marca { display: flex; align-items: baseline; gap: .75rem; flex-wrap: wrap;
  border-bottom: 1px solid rgba(20,33,43,0.14); padding-bottom: .6rem; margin-bottom: .25rem; }
.dd-marca__nombre { font-family: var(--dd-titulos); font-weight: 760; font-stretch: 82%; font-size: 1.45rem;
  color: var(--dd-tinta); letter-spacing: -.01em; }
.dd-marca__lema { font-family: var(--dd-numeros); font-size: .7rem; text-transform: uppercase;
  letter-spacing: .08em; color: var(--dd-tinta-suave); }

/* Encabezado del caso: vidrio con isobaras, y una franja que baja de la lluvia a la tierra seca */
.dd-caso { position: relative; background-image: url("$curvas") !important; background-repeat: no-repeat;
  background-position: right -40px top -10px; background-size: 640px 260px;
  padding: 1.35rem 1.6rem 1.45rem 1.9rem; margin: .5rem 0 1.25rem; overflow: hidden; }
.dd-caso::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 7px;
  background: linear-gradient(180deg, $lluvia 0%, $senal 55%, $tierra 100%); }
.dd-caso__numero { font-family: var(--dd-numeros); font-size: .74rem; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: var(--dd-tinta-suave); margin: 0 0 .5rem; }
.dd-caso__numero::before { content: ""; display: inline-block; width: .55rem; height: .55rem; border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #fff 0%, $lluvia 60%); margin-right: .55rem; vertical-align: .05rem; }
/* Streamlit fija el tamaño de los párrafos del markdown: estas reglas necesitan !important. */
.dd-caso p.dd-caso__pregunta { font-family: var(--dd-titulos) !important; font-weight: 780; font-stretch: 80%;
  color: var(--dd-tinta); font-size: clamp(2rem, 4.2vw, 3.2rem) !important; line-height: 1 !important;
  letter-spacing: -.02em; margin: 0 !important; max-width: 20ch; font-optical-sizing: auto; }
.dd-caso p.dd-caso__numero { font-size: .74rem !important; }
.dd-caso p.dd-caso__nota { font-size: 1rem !important; color: var(--dd-tinta-suave); margin: .7rem 0 0 !important;
  max-width: 60ch; }
p.dd-veredicto__texto { font-size: 1.08rem !important; }

/* Veredicto como sello, sobre un vidrio propio */
.dd-veredicto { display: flex; align-items: center; gap: 1.25rem 1.75rem; flex-wrap: wrap; margin: .25rem 0 1rem;
  padding: .9rem 1.1rem; border-radius: 14px; background: rgba(255,255,255,0.42);
  -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.6); }
.dd-sello { display: inline-block; transform: rotate(-1.5deg); border: 5px double currentColor;
  border-radius: 4px; padding: .55rem 1rem .5rem; font-family: var(--dd-numeros); font-weight: 700;
  font-size: 1.05rem; letter-spacing: .06em; text-transform: uppercase; white-space: nowrap; max-width: 100%;
  box-shadow: 0 6px 18px -10px rgba(20,33,43,0.5); }
.dd-sello__icono { margin-right: .45rem; }
.dd-veredicto__texto { flex: 1 1 20rem; font-size: 1.08rem; line-height: 1.55; color: var(--dd-tinta); margin: 0; }
@keyframes dd-sellar { from { opacity: 0; transform: rotate(-1.5deg) scale(1.14); }
  to { opacity: 1; transform: rotate(-1.5deg) scale(1); } }
@media (prefers-reduced-motion: no-preference) { .dd-sello { animation: dd-sellar 180ms ease-out both; } }

.dd-faltan { font-size: .98rem; color: var(--dd-tinta-suave); border-left: 3px solid var(--dd-senal);
  padding: .1rem 0 .1rem .75rem; margin: -.25rem 0 1rem; }

/* Evidencias numeradas (mismo alto en la fila) */
[data-testid="stHorizontalBlock"]:has([class*="st-key-evidencia"]) { align-items: stretch; }
[data-testid="stColumn"]:has([class*="st-key-evidencia"]) { align-self: stretch; }
[data-testid="stColumn"]:has([class*="st-key-evidencia"]) [data-testid="stVerticalBlock"],
[data-testid="stColumn"]:has([class*="st-key-evidencia"]) [data-testid="stLayoutWrapper"] { height: 100%; }
[data-testid="stMetricLabel"] p { font-family: var(--dd-numeros); font-size: .68rem !important; font-weight: 600;
  letter-spacing: .06em; text-transform: uppercase; color: var(--dd-tinta-suave); }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { white-space: normal !important;
  overflow: visible !important; text-overflow: clip !important; }
[data-testid="stMetricValue"] { font-family: var(--dd-numeros); font-variant-numeric: tabular-nums;
  letter-spacing: -.03em; color: var(--dd-tinta); font-size: clamp(1.35rem, 2vw, 1.85rem) !important;
  line-height: 1.15 !important; }
/* Unidades largas: que el número baje de línea en vez de cortarse con puntos suspensivos */
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { white-space: normal !important;
  overflow: visible !important; text-overflow: clip !important; }
[class*="st-key-evidencia"] [data-testid="stCaptionContainer"] p { font-size: .9rem; line-height: 1.45; }

/* Pestañas: una barra de vidrio, como la de un tablero de estación. Si no caben, pasan a otra fila:
   las seis se ven siempre, también en el celular. */
[data-testid="stTabs"] [role="tablist"] { flex-wrap: wrap; gap: .25rem; padding: .35rem; border-radius: 18px;
  overflow: visible; background: rgba(255,255,255,0.5); -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.7); box-shadow: var(--dd-sombra); margin-bottom: .6rem; }
[data-testid="stTabs"] [role="tablist"]::after { display: none !important; }
[data-testid="stTab"] p, [role="tab"] p { font-family: var(--dd-numeros) !important; font-size: .7rem !important;
  font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }
[role="tab"] { border-radius: 12px; padding: .4rem .75rem !important; height: auto !important; }
[role="tab"][aria-selected="true"] { background: $noche !important; }
[role="tab"][aria-selected="true"] p { color: #FFFFFF !important; }

/* Barra lateral: etiquetas de instrumento */
.dd-panel { font-family: var(--dd-numeros); font-size: .7rem; font-weight: 700; letter-spacing: .12em;
  text-transform: uppercase; color: var(--dd-senal); margin: 0 0 .25rem; }
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { font-family: var(--dd-numeros);
  font-size: .7rem; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; }

/* Títulos de sección con la fuente de letrero */
h1, h2, h3 { font-stretch: 82%; letter-spacing: -.01em; }

/* Pie: fuentes del expediente */
.dd-fuentes { border-top: 1px solid rgba(20,33,43,0.14); margin-top: 1.5rem; padding-top: .9rem;
  font-size: .9rem; color: var(--dd-tinta-suave); line-height: 1.55; }
.dd-fuentes__titulo { font-family: var(--dd-numeros); font-size: .7rem; font-weight: 600; letter-spacing: .1em;
  text-transform: uppercase; color: var(--dd-tinta); margin: 0 0 .35rem; }
.dd-fuentes a { color: var(--dd-tinta); text-decoration-color: var(--dd-senal); text-underline-offset: 3px; }

/* Foco visible con teclado: anillo de tinta + halo ámbar (en la barra oscura, solo ámbar) */
:focus-visible { outline: 3px solid var(--dd-tinta) !important; outline-offset: 2px;
  box-shadow: 0 0 0 6px var(--dd-senal) !important; }
section[data-testid="stSidebar"] :focus-visible { outline-color: var(--dd-senal) !important; box-shadow: none !important; }
/* La fila de pestañas recorta lo que sale de ella: ahí el anillo va por dentro */
[role="tab"]:focus-visible { outline-offset: -3px; box-shadow: none !important; background: $senal_suave; }

/* Recuadro "¿Qué significa?" y "Fuente y limitaciones" */
.dd-significa { position: relative; padding: .95rem 1.2rem .95rem 1.45rem; margin: .25rem 0 1.1rem; overflow: hidden; }
.dd-significa::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: linear-gradient(180deg, $lluvia, $senal); }
p.dd-etiqueta { font-family: var(--dd-numeros); font-size: .68rem !important; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: var(--dd-tinta-suave); margin: 0 0 .35rem !important; }
.dd-significa p.dd-significa__texto { font-size: 1.02rem !important; line-height: 1.55; margin: 0 !important; color: var(--dd-tinta); }
.dd-significa p.dd-significa__no { font-size: .96rem !important; margin: .55rem 0 0 !important; color: var(--dd-tinta); }
.dd-limites { border-top: 1px dashed rgba(20,33,43,0.2); margin-top: 1.25rem; padding-top: .6rem; }
.dd-limites p { font-size: .9rem !important; color: var(--dd-tinta-suave); margin: 0 0 .2rem !important; line-height: 1.5; }

/* Tarjetas del resumen, en palabras: vidrio con una franja del color del veredicto */
.dd-tarjetas { display: grid; grid-template-columns: repeat(auto-fit, minmax(11.5rem, 1fr)); gap: .9rem; margin: .5rem 0 1.25rem; }
.dd-tarjeta { position: relative; padding: 1rem 1.05rem .95rem; overflow: hidden; }
.dd-tarjeta::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 4px; background: currentColor; }
.dd-tarjeta p { margin: 0 !important; }
.dd-tarjeta p.dd-tarjeta__valor { font-family: var(--dd-numeros); font-weight: 700; font-size: 1.05rem !important;
  line-height: 1.3; margin: .25rem 0 .4rem !important; }
.dd-tarjeta p.dd-tarjeta__texto { font-size: .95rem !important; line-height: 1.45; color: var(--dd-tinta); }

/* Resumen en palabras sencillas */
.dd-resumen { padding: 1.2rem 1.45rem; }
.dd-resumen p.dd-resumen__titular { font-family: var(--dd-titulos); font-weight: 760; font-stretch: 82%;
  font-size: clamp(1.45rem, 2.8vw, 2rem) !important; line-height: 1.08 !important; margin: 0 0 .55rem !important;
  color: var(--dd-tinta); letter-spacing: -.015em; }
.dd-resumen p, .dd-resumen li { font-size: 1.02rem !important; line-height: 1.55; }
.dd-resumen ul { margin: .4rem 0 .8rem 1.1rem; padding: 0; }
.dd-resumen .dd-resumen__tema { font-family: var(--dd-numeros); font-size: .66rem; letter-spacing: .06em;
  text-transform: uppercase; color: var(--dd-lluvia); margin-right: .45rem; }
.dd-resumen p.dd-resumen__origen { font-size: .88rem !important; color: var(--dd-tinta-suave); margin-top: .6rem !important; }

/* Leyenda del mapa */
.dd-leyenda { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; font-size: .92rem; color: var(--dd-tinta);
  margin: .4rem 0; }
.dd-leyenda__barra { width: 11rem; max-width: 45vw; height: .7rem; border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.8); background: linear-gradient(90deg, $menos_agua, $papel, $mas_agua); }
.dd-leyenda__muestra { display: inline-block; width: 1.6rem; height: 1rem; border-radius: 3px; background: rgba(255,255,255,0.7); }
.dd-leyenda__muestra--segura { border: 4px solid var(--dd-tinta); }
.dd-leyenda__muestra--no { border: 2px dashed var(--dd-tinta-suave); }

/* Pantallas angostas (375 px) */
@media (max-width: 640px) {
  .dd-caso { padding: 1.05rem 1rem 1.15rem 1.3rem; background-position: right -260px top -30px; }
  .dd-sello { white-space: normal; font-size: .95rem; }
  .dd-marca__lema { display: none; }
  [data-testid="stTabs"] [data-baseweb="tab-list"] { border-radius: 16px; }
}
""")

CSS = "<style>" + _CSS.substitute(
    papel=PAPEL, tarjeta=TARJETA, tinta=TINTA, tinta_suave=TINTA_SUAVE, linea=LINEA, senal=SENAL,
    lluvia=LLUVIA, tierra=TIERRA, niebla=NIEBLA, bruma=BRUMA, polvo=POLVO, noche=NOCHE, noche_2=NOCHE_2,
    vidrio=VIDRIO, vidrio_borde=VIDRIO_BORDE, grietas=GRIETAS_URL,
    pila_texto=PILA_TEXTO, pila_titulos=PILA_TITULOS, pila_numeros=PILA_NUMEROS, curvas=CURVAS_URL,
    senal_suave=rgba(SENAL, 0.22), menos_agua=MENOS_AGUA, mas_agua=MAS_AGUA,
) + "</style>"

# --- Plantilla de Plotly -------------------------------------------------------------------
_EJE = dict(gridcolor="rgba(20,33,43,0.10)", griddash="dot", gridwidth=1, linecolor="rgba(20,33,43,0.18)", zerolinecolor=TINTA_SUAVE,
            tickfont=dict(family=PILA_NUMEROS, size=12, color=TINTA_SUAVE),
            title=dict(font=dict(family=PILA_TEXTO, size=13, color=TINTA_SUAVE)))
PLANTILLA = go.layout.Template(layout=dict(
    font=dict(family=PILA_TEXTO, size=14, color=TINTA),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=_EJE, yaxis=_EJE,
    hoverlabel=dict(bgcolor="rgba(251,252,252,0.94)", bordercolor=LINEA, font=dict(family=PILA_NUMEROS, size=13, color=TINTA)),
    legend=dict(font=dict(family=PILA_TEXTO, size=13, color=TINTA_SUAVE), bgcolor="rgba(0,0,0,0)"),
    separators=".,",
))
SERIE_MENSUAL = dict(color=rgba(TINTA_SUAVE, 0.55), width=1)

# Configuración de las gráficas: sin logo de Plotly y fechas en el idioma de la app ("mar 1998" / "Mar 1998").
def config_grafica(idioma: str) -> dict:
    if idioma == "en":
        return {"displaylogo": False}  # Plotly ya viene en inglés
    meses, dias = T.MESES["es"], T.DIAS["es"]
    return {
        "displaylogo": False,
        "locale": "es-dd",
        "locales": {"es-dd": {"format": {
            "months": meses, "shortMonths": [m[:3] for m in meses], "days": dias, "shortDays": [d[:3] for d in dias],
            "decimal": ".", "thousands": ",",
        }}},
    }


CONFIG_GRAFICA = config_grafica("es")
FORMATO_MES = "%b %Y"  # encabezado del recuadro al pasar el mouse: "mar 1998" / "Mar 1998"


def _mezcla(a: str, b: str, t: float) -> str:
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def color_cambio(valor: float, maximo: float) -> str:
    """Escala divergente del mapa: tierra colorada = hacia menos agua, niebla = sin cambio, lluvia = hacia más agua."""
    if valor is None or maximo <= 0 or valor != valor:  # NaN
        return LINEA
    t = max(-1.0, min(1.0, valor / maximo))
    return _mezcla(PAPEL, MAS_AGUA if t > 0 else MENOS_AGUA, abs(t))


def anotacion(x, y, texto: str, color: str, derecha: bool) -> dict:
    """Etiqueta de inicio o fin de la tendencia ("1994: 13.3 °C")."""
    return dict(x=x, y=y, text=texto, showarrow=True, arrowhead=0, arrowwidth=1.5, arrowcolor=color,
                ax=-36 if derecha else 36, ay=-48 if derecha else 48, xanchor="right" if derecha else "left",
                font=dict(family=PILA_NUMEROS, size=13, color=TINTA), align="left",
                bgcolor="rgba(251,252,252,0.9)", bordercolor=color, borderwidth=1.5, borderpad=5)


# --- Piezas HTML ---------------------------------------------------------------------------
def marca_html(idioma: str = "es") -> str:
    return (f'<div class="dd-marca"><span class="dd-marca__nombre">{T.t("marca.nombre", idioma)}</span>'
            f'<span class="dd-marca__lema">{T.t("marca.lema", idioma)}</span></div>')


def caso_html(numero: str, pregunta: str, nota: str, idioma: str = "es") -> str:
    """Encabezado de expediente: número de caso en mono y la pregunta grande."""
    return (f'<div class="dd-caso"><p class="dd-caso__numero">{T.t("caso.prefijo", idioma)} {html.escape(numero)}</p>'
            f'<p class="dd-caso__pregunta" role="heading" aria-level="2">{html.escape(pregunta)}</p>'
            f'<p class="dd-caso__nota">{nota}</p></div>')


def sello_html(color: str, texto: str, idioma: str = "es") -> str:
    """Veredicto como sello: ícono + VEREDICTO: PALABRA, y la explicación al lado."""
    v = VEREDICTO[color]
    return (f'<div class="dd-veredicto"><div class="dd-sello" style="color:{v["tinta"]};background:{v["fondo"]}">'
            f'<span class="dd-sello__icono" aria-hidden="true">{v["icono"]}</span>{T.t("sello.veredicto", idioma)}: '
            f'{palabra(color, idioma)}</div><p class="dd-veredicto__texto">{html.escape(texto)}</p></div>')


def faltan_html(anios: int, idioma: str = "es") -> str:
    return f'<p class="dd-faltan">{T.t("faltan", idioma, n=anios)}</p>'


def fuentes_html(creditos_html: str, idioma: str = "es") -> str:
    return (f'<div class="dd-fuentes"><p class="dd-fuentes__titulo">{T.t("etq.fuentes", idioma)}</p>'
            f'{creditos_html}</div>')


def panel_html(idioma: str = "es") -> str:
    return f'<p class="dd-panel">{T.t("panel.titulo", idioma)}</p>'


def significa_html(texto: str, no_es: str | None = None, idioma: str = "es") -> str:
    """Recuadro "¿Qué significa?" con su "Qué no es" opcional."""
    extra = (f'<p class="dd-significa__no"><strong>{T.t("etq.que_no_es", idioma)}</strong> {html.escape(no_es)}</p>'
             if no_es else "")
    return (f'<div class="dd-significa"><p class="dd-etiqueta">{T.t("etq.que_significa", idioma)}</p>'
            f'<p class="dd-significa__texto">{html.escape(texto)}</p>{extra}</div>')


def limites_html(fuente: str, limite: str, idioma: str = "es") -> str:
    return (f'<div class="dd-limites"><p class="dd-etiqueta">{T.t("etq.fuente_limites", idioma)}</p>'
            f'<p>{html.escape(fuente)}</p><p>{html.escape(limite)}</p></div>')


def tarjetas_html(tarjetas: list[dict]) -> str:
    """Tarjetas del resumen: [{tema, icono, valor, texto, color}]. Ícono + palabras, no solo color."""
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
    """Escala de color y qué borde marca una tendencia segura (las dos pruebas coinciden)."""
    return (f'<div class="dd-leyenda"><span><span aria-hidden="true">▼</span> {T.t("leyenda.menos", idioma)} '
            f'(−{maximo:.2f} {html.escape(unidades)} {T.t("leyenda.por_decada", idioma)})</span>'
            f'<span class="dd-leyenda__barra" aria-hidden="true"></span><span><span aria-hidden="true">▲</span> '
            f'{T.t("leyenda.mas", idioma)} (+{maximo:.2f})</span></div>'
            f'<div class="dd-leyenda"><span class="dd-leyenda__muestra dd-leyenda__muestra--segura" aria-hidden="true">'
            f'</span><span>{T.t("leyenda.segura", idioma)}</span><span class="dd-leyenda__muestra '
            f'dd-leyenda__muestra--no" aria-hidden="true"></span><span>{T.t("leyenda.no_segura", idioma)}</span>'
            f'<strong>{T.t("leyenda.cuenta", idioma, n=seguras, total=total)}</strong></div>')
