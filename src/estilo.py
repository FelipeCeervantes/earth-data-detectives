"""Identidad visual "Expediente de campo": tokens, CSS (una sola inyección), plantilla de Plotly y piezas HTML.

Todo lo visual vive aquí; app.py solo lo usa. No calcula nada.
Capas de tokens: primitivos (hex) → semánticos (para qué se usan) → componentes (veredicto, gráfica).
"""

from __future__ import annotations

import html
from string import Template
from urllib.parse import quote

import plotly.graph_objects as go

from src import textos as T

# --- 1. Primitivos -------------------------------------------------------------------------
PAPEL = "#F5F0E6"
TARJETA = "#FFFDF8"
TINTA = "#1B2430"
TINTA_SUAVE = "#5B6472"
LINEA = "#D9CFBD"
SENAL = "#E09F3E"  # acento de marca: detalles y foco, nunca texto sobre papel
TINTA_PANEL = "#26303D"  # campos dentro de la barra lateral oscura

FUENTE_TITULOS = "Fraunces"
FUENTE_TEXTO = "Atkinson Hyperlegible"
FUENTE_NUMEROS = "IBM Plex Mono"

# --- 2. Semánticos -------------------------------------------------------------------------
FONDO = PAPEL
SUPERFICIE = TARJETA
TEXTO = TINTA
TEXTO_SECUNDARIO = TINTA_SUAVE
BORDE = LINEA
FOCO = SENAL
PILA_TEXTO = f"'{FUENTE_TEXTO}', 'Segoe UI', system-ui, sans-serif"
PILA_TITULOS = f"'{FUENTE_TITULOS}', Georgia, serif"
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
MENOS_AGUA = "#A83F1B"   # óxido
MAS_AGUA = "#1F6F8B"     # azul petróleo


def palabra(color: str, idioma: str) -> str:
    """Palabra del veredicto ("Sube" / "Rising") para un color de src.analisis.veredicto."""
    return VEREDICTO[color]["palabra_en" if idioma == "en" else "palabra"]


def rgba(hex_color: str, alfa: float) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alfa})"


# --- Textura: curvas de nivel (SVG en CSS, opacidad baja) ----------------------------------
_CURVAS_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='640' height='260' viewBox='0 0 640 260'>"
    f"<g fill='none' stroke='{LINEA}' stroke-width='1.2' stroke-opacity='0.9'>"
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
CURVAS_URL = "data:image/svg+xml;utf8," + quote(_CURVAS_SVG)

# --- CSS (una sola inyección) --------------------------------------------------------------
_CSS = Template("""
/* Expediente de campo: lo que el tema nativo de Streamlit no cubre */
:root {
  --dd-papel: $papel; --dd-tarjeta: $tarjeta; --dd-tinta: $tinta; --dd-tinta-suave: $tinta_suave;
  --dd-linea: $linea; --dd-senal: $senal;
  --dd-texto: $pila_texto; --dd-titulos: $pila_titulos; --dd-numeros: $pila_numeros;
}

/* Marca superior */
.dd-marca { display: flex; align-items: baseline; gap: .75rem; flex-wrap: wrap;
  border-bottom: 1px solid var(--dd-linea); padding-bottom: .6rem; margin-bottom: .25rem; }
.dd-marca__nombre { font-family: var(--dd-titulos); font-weight: 700; font-size: 1.35rem;
  color: var(--dd-tinta); letter-spacing: -.01em; }
.dd-marca__lema { font-family: var(--dd-numeros); font-size: .78rem; text-transform: uppercase;
  letter-spacing: .1em; color: var(--dd-tinta-suave); }

/* Encabezado de expediente con curvas de nivel */
.dd-caso { position: relative; background-color: var(--dd-tarjeta);
  background-image: url("$curvas"); background-repeat: no-repeat; background-position: right -40px top -10px;
  background-size: 640px 260px; border: 1px solid var(--dd-linea); border-left: 6px solid var(--dd-tinta);
  border-radius: 4px; padding: 1.25rem 1.5rem 1.35rem; margin: .5rem 0 1.25rem; overflow: hidden; }
.dd-caso__numero { font-family: var(--dd-numeros); font-size: .8rem; font-weight: 600; letter-spacing: .12em;
  text-transform: uppercase; color: var(--dd-tinta-suave); margin: 0 0 .4rem; }
.dd-caso__numero::before { content: ""; display: inline-block; width: .6rem; height: .6rem;
  background: var(--dd-senal); margin-right: .55rem; vertical-align: .05rem; }
/* Streamlit fija el tamaño de los párrafos del markdown: estas reglas necesitan !important.
   Ojo: nada de etiquetas HTML escritas dentro de esta CSS, o st.html descarta todo el bloque. */
.dd-caso p.dd-caso__pregunta { font-family: var(--dd-titulos) !important; font-weight: 650; color: var(--dd-tinta);
  font-size: clamp(1.8rem, 3.6vw, 2.75rem) !important; line-height: 1.08 !important; letter-spacing: -.015em;
  margin: 0 !important; max-width: 22ch; font-variation-settings: "opsz" 96; }
.dd-caso p.dd-caso__numero { font-size: .8rem !important; }
.dd-caso p.dd-caso__nota { font-size: .98rem !important; color: var(--dd-tinta-suave); margin: .6rem 0 0 !important;
  max-width: 60ch; }
p.dd-veredicto__texto { font-size: 1.08rem !important; }

/* Veredicto como sello */
.dd-veredicto { display: flex; align-items: center; gap: 1.25rem 1.75rem; flex-wrap: wrap; margin: .25rem 0 1rem; }
.dd-sello { display: inline-block; transform: rotate(-1.5deg); border: 5px double currentColor;
  border-radius: 3px; padding: .55rem 1rem .5rem; font-family: var(--dd-numeros); font-weight: 700;
  font-size: 1.2rem; letter-spacing: .1em; text-transform: uppercase; white-space: nowrap; max-width: 100%; }
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
[class*="st-key-evidencia"] { background: var(--dd-tarjeta); }
[data-testid="stMetricLabel"] p { font-family: var(--dd-numeros); font-size: .74rem !important; font-weight: 600;
  letter-spacing: .08em; text-transform: uppercase; color: var(--dd-tinta-suave); }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { white-space: normal !important;
  overflow: visible !important; text-overflow: clip !important; }
[data-testid="stMetricValue"] { font-family: var(--dd-numeros); font-variant-numeric: tabular-nums;
  letter-spacing: -.02em; color: var(--dd-tinta); font-size: clamp(1.45rem, 2.1vw, 2rem) !important;
  line-height: 1.15 !important; }
/* Unidades largas (mm/día, kWh/m²/día): que el número baje de línea en vez de cortarse con "…" */
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { white-space: normal !important;
  overflow: visible !important; text-overflow: clip !important; }
[class*="st-key-evidencia"] [data-testid="stCaptionContainer"] p { font-size: .9rem; line-height: 1.45; }

/* Pestañas y barra lateral: etiquetas de instrumento */
[data-testid="stTab"] p, [role="tab"] p { font-family: var(--dd-numeros) !important; font-size: .82rem !important;
  font-weight: 600; letter-spacing: .08em; text-transform: uppercase; }
.dd-panel { font-family: var(--dd-numeros); font-size: .76rem; font-weight: 600; letter-spacing: .14em;
  text-transform: uppercase; color: var(--dd-senal); margin: 0 0 .25rem; }
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { font-family: var(--dd-numeros);
  font-size: .78rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; }

/* Pie: fuentes del expediente */
.dd-fuentes { border-top: 1px solid var(--dd-linea); margin-top: 1.5rem; padding-top: .9rem;
  font-size: .9rem; color: var(--dd-tinta-suave); line-height: 1.55; }
.dd-fuentes__titulo { font-family: var(--dd-numeros); font-size: .74rem; font-weight: 600; letter-spacing: .14em;
  text-transform: uppercase; color: var(--dd-tinta); margin: 0 0 .35rem; }
.dd-fuentes a { color: var(--dd-tinta); text-decoration-color: var(--dd-senal); text-underline-offset: 3px; }

/* Foco visible con teclado: anillo de tinta + halo de señal (en la barra oscura, solo señal) */
:focus-visible { outline: 3px solid var(--dd-tinta) !important; outline-offset: 2px;
  box-shadow: 0 0 0 6px var(--dd-senal) !important; }
section[data-testid="stSidebar"] :focus-visible { outline-color: var(--dd-senal) !important; box-shadow: none !important; }
/* La fila de pestañas recorta lo que sale de ella: ahí el anillo va por dentro */
[role="tab"]:focus-visible { outline-offset: -3px; box-shadow: none !important; background: $senal_suave; }

/* Recuadro "¿Qué significa?" y "Fuente y limitaciones" */
.dd-significa { background: var(--dd-tarjeta); border: 1px solid var(--dd-linea); border-left: 4px solid var(--dd-senal);
  border-radius: 4px; padding: .85rem 1.1rem; margin: .25rem 0 1.1rem; }
p.dd-etiqueta { font-family: var(--dd-numeros); font-size: .74rem !important; font-weight: 600; letter-spacing: .12em;
  text-transform: uppercase; color: var(--dd-tinta-suave); margin: 0 0 .3rem !important; }
.dd-significa p.dd-significa__texto { font-size: 1.02rem !important; line-height: 1.55; margin: 0 !important; color: var(--dd-tinta); }
.dd-significa p.dd-significa__no { font-size: .96rem !important; margin: .55rem 0 0 !important; color: var(--dd-tinta); }
.dd-limites { border-top: 1px dashed var(--dd-linea); margin-top: 1.25rem; padding-top: .6rem; }
.dd-limites p { font-size: .9rem !important; color: var(--dd-tinta-suave); margin: 0 0 .2rem !important; line-height: 1.5; }

/* Tarjetas del resumen, en palabras */
.dd-tarjetas { display: grid; grid-template-columns: repeat(auto-fit, minmax(11.5rem, 1fr)); gap: .9rem; margin: .5rem 0 1.25rem; }
.dd-tarjeta { background: var(--dd-tarjeta); border: 1px solid var(--dd-linea); border-top: 4px solid currentColor;
  border-radius: 4px; padding: .8rem 1rem .9rem; }
.dd-tarjeta p { margin: 0 !important; }
.dd-tarjeta p.dd-tarjeta__valor { font-family: var(--dd-numeros); font-weight: 700; font-size: 1.15rem !important;
  line-height: 1.3; margin: .2rem 0 .35rem !important; }
.dd-tarjeta p.dd-tarjeta__texto { font-size: .95rem !important; line-height: 1.45; color: var(--dd-tinta); }

/* Resumen en palabras sencillas */
.dd-resumen { border: 1px solid var(--dd-linea); background: var(--dd-tarjeta); border-radius: 4px; padding: 1.1rem 1.35rem; }
.dd-resumen p.dd-resumen__titular { font-family: var(--dd-titulos); font-weight: 650;
  font-size: clamp(1.35rem, 2.6vw, 1.8rem) !important; line-height: 1.15 !important; margin: 0 0 .5rem !important;
  color: var(--dd-tinta); }
.dd-resumen p, .dd-resumen li { font-size: 1.02rem !important; line-height: 1.55; }
.dd-resumen ul { margin: .4rem 0 .8rem 1.1rem; padding: 0; }
.dd-resumen .dd-resumen__tema { font-family: var(--dd-numeros); font-size: .74rem; letter-spacing: .1em;
  text-transform: uppercase; color: var(--dd-tinta-suave); margin-right: .4rem; }
.dd-resumen p.dd-resumen__origen { font-size: .88rem !important; color: var(--dd-tinta-suave); margin-top: .6rem !important; }

/* Leyenda del mapa */
.dd-leyenda { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; font-size: .92rem; color: var(--dd-tinta);
  margin: .4rem 0; }
.dd-leyenda__barra { width: 11rem; max-width: 45vw; height: .7rem; border: 1px solid var(--dd-linea);
  background: linear-gradient(90deg, $menos_agua, $papel, $mas_agua); }

.dd-leyenda__muestra { display: inline-block; width: 1.6rem; height: 1rem; background: var(--dd-tarjeta); }
.dd-leyenda__muestra--segura { border: 4px solid var(--dd-tinta); }
.dd-leyenda__muestra--no { border: 2px dashed var(--dd-tinta-suave); }

/* Pantallas angostas (375 px) */
@media (max-width: 640px) {
  .dd-caso { padding: 1rem 1rem 1.1rem; background-position: right -260px top -30px; }
  .dd-sello { white-space: normal; font-size: 1.02rem; }
  .dd-marca__lema { display: none; }
}
""")

CSS = "<style>" + _CSS.substitute(
    papel=PAPEL, tarjeta=TARJETA, tinta=TINTA, tinta_suave=TINTA_SUAVE, linea=LINEA, senal=SENAL,
    pila_texto=PILA_TEXTO, pila_titulos=PILA_TITULOS, pila_numeros=PILA_NUMEROS, curvas=CURVAS_URL,
    senal_suave=rgba(SENAL, 0.22), menos_agua="#A83F1B", mas_agua="#1F6F8B",
) + "</style>"

# --- Plantilla de Plotly -------------------------------------------------------------------
_EJE = dict(gridcolor=LINEA, griddash="dot", gridwidth=1, linecolor=LINEA, zerolinecolor=TINTA_SUAVE,
            tickfont=dict(family=PILA_NUMEROS, size=12, color=TINTA_SUAVE),
            title=dict(font=dict(family=PILA_TEXTO, size=13, color=TINTA_SUAVE)))
PLANTILLA = go.layout.Template(layout=dict(
    font=dict(family=PILA_TEXTO, size=14, color=TINTA),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=_EJE, yaxis=_EJE,
    hoverlabel=dict(bgcolor=TARJETA, bordercolor=LINEA, font=dict(family=PILA_NUMEROS, size=13, color=TINTA)),
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
    """Escala divergente del mapa: óxido = hacia menos agua, papel = sin cambio, azul petróleo = hacia más agua."""
    if valor is None or maximo <= 0 or valor != valor:  # NaN
        return LINEA
    t = max(-1.0, min(1.0, valor / maximo))
    return _mezcla(PAPEL, MAS_AGUA if t > 0 else MENOS_AGUA, abs(t))


def anotacion(x, y, texto: str, color: str, derecha: bool) -> dict:
    """Etiqueta de inicio o fin de la tendencia ("1994: 13.3 °C")."""
    return dict(x=x, y=y, text=texto, showarrow=True, arrowhead=0, arrowwidth=1.5, arrowcolor=color,
                ax=-36 if derecha else 36, ay=-48 if derecha else 48, xanchor="right" if derecha else "left",
                font=dict(family=PILA_NUMEROS, size=13, color=TINTA), align="left",
                bgcolor=TARJETA, bordercolor=color, borderwidth=1.5, borderpad=5)


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
