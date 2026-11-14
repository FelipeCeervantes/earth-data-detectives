"""Detectives de Datos de la Tierra · Los Altos de Jalisco: app de Streamlit.

Ejecutar:  streamlit run app.py
Lo visual vive en src/estilo.py, los textos en src/textos.py; esta app solo usa las funciones de
region, catalogo, datos, indices, analisis y explicar.
"""

import os
import warnings

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import catalogo, datos, explicar, indices, region
from src import estilo as E
from src import textos as T

IDIOMA = "es"   # ponytail: fijo en español hasta la tarea 13 (botón EN/ES; la app abrirá en inglés)
from src.analisis import (anios_para_significancia, anomalias, cambio_total, mann_kendall, tendencia_ols,
                          veredicto)

st.set_page_config(page_title="Detectives de Datos de la Tierra · Los Altos", page_icon=":material/water_drop:",
                   layout="wide")
st.html(E.CSS)

ANIO_MIN, ANIO_MAX = 1981, 2024      # lo que hay en POWER mensual; se descarga todo para calcular "lo normal"
PERIODO_INICIAL = (2001, 2024)
MIN_ANIOS = 10                       # con menos años, una tendencia es puro ruido
CAPAS = {"humedad_superficie": "Superficie (5 cm)", "humedad_raices": "Zona de raíces (1 m)",
         "humedad_perfil": "Perfil completo"}
CAPA_INICIAL = "humedad_raices"
SEGURAS = ("rojo", "verde")          # veredicto "sube" o "baja": las dos pruebas coinciden
CREDITOS = (
    '<a href="https://power.larc.nasa.gov/">NASA POWER</a> (NASA Langley Research Center), con datos del modelo '
    '<a href="https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/">MERRA-2</a> (NASA GMAO): lluvia y humedad del suelo. '
    'Límites municipales: <a href="https://www.inegi.org.mx/temas/mg/">Marco Geoestadístico de INEGI</a> '
    "(Encuesta Intercensal 2025). Sequía: SPI (McKee y colegas, 1993). Hecho por el equipo Detectives de Datos "
    "de la Tierra para el NASA Space Apps Challenge."
)
AYUDA_P = ("El p-valor dice qué tan probable sería ver una tendencia así si en realidad no hubiera ninguna. "
           "Menos de 0.05 = es muy poco probable que sea casualidad.")


# --- Datos (con caché) ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def cargar(id_variable: str, id_zona: str) -> tuple[pd.Series, list[str]]:
    """Serie de la zona de 1981 a 2024 (para calcular "lo normal") y los avisos de src.datos."""
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        serie = datos.serie_zona(id_variable, id_zona, ANIO_MIN, ANIO_MAX)
    return serie, list(dict.fromkeys(str(a.message) for a in avisos))


def _clave_gemini() -> str | None:
    try:
        clave = st.secrets.get("GEMINI_API_KEY")
    except Exception:  # sin archivo de secrets
        clave = None
    return clave or os.environ.get("GEMINI_API_KEY")


@st.cache_data(show_spinner=False)
def calcular_resumen(id_zona: str, a0: int, a1: int, _clave: str | None) -> tuple[dict, dict, bool]:
    """Resultados ya calculados (src.explicar) y su resumen en palabras: con Gemini si hay clave, si no, plantillas."""
    lluvia, _ = cargar("precipitacion", id_zona)
    humedad, _ = cargar(CAPA_INICIAL, id_zona)
    r = explicar.resultados(region.obtener_zona(id_zona)["nombre"], (a0, a1), lluvia, humedad,
                            capa="zona de raíces", idioma=IDIOMA)
    con_ia = explicar.resumen_con_gemini(r, clave=_clave, idioma=IDIOMA) if _clave else None
    return r, (con_ia or explicar.resumen_sin_ia(r, idioma=IDIOMA)), con_ia is not None


@st.cache_data(show_spinner=False)
def tendencias_celdas(id_variable: str, id_zona: str, a0: int, a1: int) -> pd.DataFrame:
    """Tendencia por década en cada celda de POWER de la zona (para el mapa)."""
    filas = []
    for c in region.celdas(id_zona):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # el aviso de "sin conexión" ya se muestra arriba
            serie = datos.serie_punto(id_variable, c["lat"], c["lon"], ANIO_MIN, ANIO_MAX).loc[f"{a0}":f"{a1}"]
        anom = anomalias(serie)
        ols, mk = tendencia_ols(anom), mann_kendall(anom, metodo="hamed_rao")
        filas.append({"lat": c["lat"], "lon": c["lon"], "peso": c["peso"], "pendiente": ols["pendiente_decada"],
                      "ic_bajo": ols["ic_bajo"], "ic_alto": ols["ic_alto"],
                      "color": veredicto(ols, mk, "")["color"]})
    return pd.DataFrame(filas)


# --- Utilidades de presentación ------------------------------------------------------------
def numero(valor: float) -> str:
    return f"{valor:.1f}" if abs(valor) >= 10 else f"{valor:.2f}"


def p_texto(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
                "noviembre", "diciembre"]


def mes_texto(aaaa_mm: str) -> str:
    """'2011-01' -> 'ene 2011'."""
    anio, mes = aaaa_mm.split("-")
    return f"{MESES_LARGOS[int(mes) - 1][:3]} {anio}"


def mes_largo(fecha: pd.Timestamp) -> str:
    """-> 'enero de 2020'."""
    return f"{MESES_LARGOS[fecha.month - 1]} de {fecha.year}"


def significa(clave: str) -> None:
    st.markdown(E.significa_html(T.QUE_SIGNIFICA[clave], T.QUE_NO_ES.get(clave)), unsafe_allow_html=True)


def limites(clave: str) -> None:
    st.markdown(E.limites_html(T.FUENTE_POWER, T.LIMITES[clave]), unsafe_allow_html=True)


def evidencias(lista: list[tuple[str, str, str, str]], clave: str) -> None:
    """Fila de tarjetas EVIDENCIA 01…: [(título, valor, nota, ayuda)]."""
    for i, (col, (titulo, valor, nota, ayuda)) in enumerate(zip(st.columns(len(lista)), lista), start=1):
        with col.container(border=True, key=f"evidencia_{clave}_{i}"):
            st.metric(f"Evidencia {i:02d} · {titulo}", valor, help=ayuda or None)
            st.caption(nota)


def bloque_tendencia(serie: pd.Series, var: dict, a0: int, a1: int, clave: str) -> None:
    """Veredicto como sello, evidencias, gráfica (real o anomalías) con la tendencia y descarga CSV."""
    u = var["unidades"]
    anom = anomalias(serie)
    try:
        ols, mk = tendencia_ols(anom), mann_kendall(anom, metodo="hamed_rao")
    except ValueError as e:
        st.warning(f"No hay suficientes datos para calcular una tendencia: {e}")
        return
    v = veredicto(ols, mk, u, idioma=IDIOMA)
    color = E.VEREDICTO[v["color"]]["tinta"]
    st.markdown(E.sello_html(v["color"], v["texto"]), unsafe_allow_html=True)
    faltan = anios_para_significancia(ols)
    if faltan:
        st.markdown(E.faltan_html(max(1, round(faltan))), unsafe_allow_html=True)

    total = cambio_total(serie, ols)
    valor_total = f"{total['cambio']:+.2f} {u}"
    if total["porcentaje"] is not None and var["tipo"] == "lluvia":  # en humedad (ya en %) confundiría
        valor_total += f" ({total['porcentaje']:+.1f} %)"
    evidencias([
        ("Cambio por década", f"{ols['pendiente_decada']:+.2f} {u}",
         f"Con 95 % de confianza, entre {ols['ic_bajo']:+.2f} y {ols['ic_alto']:+.2f}.",
         f"Cuánto sube (+) o baja (−) en promedio cada 10 años. Otra forma de medirlo (Sen): "
         f"{mk['pendiente_sen_decada']:+.2f} {u}."),
        (f"En {total['anios']:.0f} años", valor_total, "Lo que cambió en todo el periodo, según la tendencia.",
         "No es la diferencia entre el primer y el último mes, que depende mucho del clima de esos días."),
        ("Prueba de la recta", p_texto(ols["p_valor"]),
         "p-valor de la regresión. Menos de 0.05: muy poco probable que sea casualidad.",
         "Prueba 1, recta de tendencia. " + AYUDA_P),
        ("Prueba de Mann-Kendall", p_texto(mk["p_valor"]), "p-valor, corregido porque cada mes se parece al anterior.",
         "Prueba 2, cuenta cuántas veces los datos suben o bajan con el tiempo. " + AYUDA_P),
    ], clave)

    vista = st.radio("Ver en la gráfica", ["Valores reales", "Anomalías"], horizontal=True, key=f"vista_{clave}",
                     help="Anomalía = diferencia con el promedio de ese mes. Quita el ciclo de las estaciones "
                          "para que se vea mejor la tendencia.")
    s = (serie if vista == "Valores reales" else anom).dropna()
    t = np.asarray(((s.index.year + (s.index.month - 1) / 12) - s.index.year[0]) / 10)
    tc, yc = t.mean(), s.mean()
    recta = yc + ols["pendiente_decada"] * (t - tc)
    lo, hi = yc + ols["ic_bajo"] * (t - tc), yc + ols["ic_alto"] * (t - tc)
    fig = go.Figure([
        go.Scatter(x=s.index, y=s, name="Valor mensual" if vista == "Valores reales" else "Anomalía mensual",
                   line=E.SERIE_MENSUAL, hovertemplate=f"%{{y:.1f}} {u}"),
        go.Scatter(x=s.index, y=np.maximum(lo, hi), line=dict(width=0), showlegend=False, hoverinfo="skip"),
        go.Scatter(x=s.index, y=np.minimum(lo, hi), fill="tonexty", fillcolor=E.rgba(color, 0.16),
                   line=dict(width=0), name="Margen de la tendencia (IC 95 %)", hoverinfo="skip"),
        go.Scatter(x=s.index, y=recta, name="Tendencia", line=dict(color=color, width=4),
                   hovertemplate=f"%{{y:.1f}} {u}"),
    ])
    fig.update_layout(
        template=E.PLANTILLA, height=420, margin=dict(t=40, b=10, l=10, r=10), hovermode="x unified",
        xaxis_title="Año", yaxis_title=f"{'Valor' if vista == 'Valores reales' else 'Anomalía'} ({u})",
        xaxis_hoverformat=E.FORMATO_MES, legend=dict(orientation="h", y=1.14, x=0),
        annotations=[
            E.anotacion(s.index[0], recta[0], f"{s.index[0].year}: {numero(recta[0])} {u}", color, derecha=False),
            E.anotacion(s.index[-1], recta[-1], f"{s.index[-1].year}: {numero(recta[-1])} {u}<br><b>"
                        f"{total['cambio']:+.2f} {u} en {total['anios']:.0f} años</b>", color, derecha=True),
        ],
    )
    st.plotly_chart(fig, width="stretch", config=E.CONFIG_GRAFICA, key=f"grafica_{clave}")
    if vista == "Anomalías":
        st.caption(f"Anomalía = diferencia con el promedio de ese mes en {a0}–{a1}.")
    tabla = pd.DataFrame({"fecha": serie.index.strftime("%Y-%m"), var["id"]: serie.values, "anomalia": anom.values})
    st.download_button(f"Descargar {var['nombre'].lower()} (CSV)", tabla.to_csv(index=False).encode("utf-8"),
                       file_name=f"{var['id']}_{id_zona}_{a0}_{a1}.csv", mime="text/csv",
                       icon=":material/download:", key=f"descarga_{clave}")


def grafica_indice(serie: pd.Series, indice: str, titulo_y: str, clave: str) -> None:
    """Barras mensuales del índice coloreadas por categoría, con bandas de fondo moderada/severa/extrema."""
    cats = [indices.categoria(float(v), indice, idioma=IDIOMA) for v in serie]
    un_mes = 27 * 24 * 3600 * 1000  # ancho de cada barra, en milisegundos (eje de fechas)
    fig = go.Figure()
    for desde, hasta, nivel, nombre in E.BANDAS:
        fig.add_hrect(y0=desde, y1=hasta, fillcolor=E.rgba(E.NIVEL[nivel]["color"], 0.10), line_width=0)
        fig.add_annotation(xref="paper", x=1.01, xanchor="left", y=(max(desde, -3.5) + hasta) / 2, text=nombre,
                           showarrow=False, font=dict(family=E.PILA_NUMEROS, size=11, color=E.NIVEL[nivel]["color"]))
    for nivel in ("humedo", "normal", "moderado", "severo", "extremo"):
        mascara = [c["nivel"] == nivel for c in cats]
        if not any(mascara):
            continue
        sub = serie[mascara]
        nombre = indices.NOMBRES[IDIOMA][indice][nivel]
        fig.add_bar(x=sub.index, y=sub.values, name=f"{E.NIVEL[nivel]['icono']} {nombre}", width=un_mes,
                    marker=dict(color=E.NIVEL[nivel]["color"], line=dict(width=0)),
                    hovertemplate=f"%{{y:+.2f}} · {nombre}<extra></extra>")
    fig.update_layout(template=E.PLANTILLA, height=380, margin=dict(t=40, b=10, l=10, r=70), barmode="overlay",
                      bargap=0, xaxis_title="Año", yaxis_title=titulo_y, xaxis_hoverformat=E.FORMATO_MES,
                      yaxis=dict(range=[-3.5, 3.5], zeroline=True, zerolinewidth=1.5),
                      xaxis=dict(range=[serie.index[0] - pd.DateOffset(months=1), serie.index[-1] + pd.DateOffset(months=1)]),
                      legend=dict(orientation="h", y=1.14, x=0), hovermode="x")
    st.plotly_chart(fig, width="stretch", config=E.CONFIG_GRAFICA, key=f"grafica_{clave}")


def evidencias_indice(res: dict, indice: str, clave: str, palabra: str) -> None:
    peor = res["peor_periodo"]
    ultimo = pd.Timestamp(res["ultimo_mes"] + "-01")
    evidencias([
        (f"Meses en {palabra}", f"{res['meses_en_deficit']} de {res['meses_totales']}",
         f"Meses con el índice en -1 o menos ({res['meses_en_deficit'] / max(res['meses_totales'], 1):.0%}).", ""),
        ("Últimos 5 años", f"{res['meses_en_deficit_ultimos']} meses en {palabra}",
         f"Desde {mes_largo(ultimo - pd.DateOffset(years=5, months=-1))} hasta {mes_largo(ultimo)}.", ""),
        ("Peor periodo", f"{mes_texto(peor[0])} – {mes_texto(peor[1])}" if peor else "Ninguno",
         res["categoria_peor"] or "No hubo meses en déficit.", "La racha más intensa de meses seguidos en -1 o menos."),
        ("Último mes", f"{res['valor_ultimo']:+.2f}", f"{mes_texto(res['ultimo_mes'])}: {res['categoria_ultimo']}.", ""),
    ], clave)


# --- Panel del detective -------------------------------------------------------------------
st.markdown(E.marca_html(), unsafe_allow_html=True)
with st.sidebar:
    st.markdown(E.panel_html(), unsafe_allow_html=True)
    id_zona = st.selectbox("1 · ¿Dónde?", list(region.ZONAS), format_func=lambda z: region.ZONAS[z]["nombre"],
                           key="zona")
    zona = region.obtener_zona(id_zona)
    st.caption(f"{len(zona['municipios'])} municipios: {', '.join(zona['municipios'])}.")
    a0, a1 = st.slider("2 · ¿En qué periodo?", ANIO_MIN, ANIO_MAX, PERIODO_INICIAL, key="periodo")
    st.caption("Lo normal: 1991–2020 · Temporada de lluvias: junio a octubre.")

lugar = "Los Altos" if id_zona == "los-altos" else zona["nombre"]
st.markdown(E.caso_html(
    f"{zona['nombre'] if id_zona != 'los-altos' else 'Los Altos'} · Lluvia y humedad del suelo · {a0}–{a1}",
    f"¿Qué está pasando con el agua en {lugar}?",
    "Elige la zona y el periodo en el panel del detective (en el celular, ábrelo con » arriba a la izquierda).",
), unsafe_allow_html=True)

if a1 - a0 + 1 < MIN_ANIOS:
    st.error(f"Elige un periodo de al menos {MIN_ANIOS} años: con menos, una tendencia no se puede distinguir "
             "de la variación normal.")
    st.stop()

try:
    with st.spinner("Descargando lluvia y humedad del suelo de NASA POWER…"):
        lluvia_toda, avisos_ll = cargar("precipitacion", id_zona)
        humedad_toda, avisos_hu = cargar(CAPA_INICIAL, id_zona)
except ValueError as e:
    st.error(f"Revisa la zona o el periodo: {e}")
    st.stop()
except Exception as e:  # sin red y sin respaldo, servidor caído: aviso en vez de romper la app
    st.error(f"No se pudieron descargar los datos de NASA POWER y no hay datos guardados. Intenta de nuevo en un "
             f"momento. ({type(e).__name__})")
    st.stop()

avisos = list(dict.fromkeys(avisos_ll + avisos_hu))
if any("Sin conexión" in a for a in avisos):
    st.warning("Sin conexión con NASA POWER: se usan los datos guardados en la app (1981–2024).",
               icon=":material/inventory_2:")
    cargar.clear()  # la próxima vez se vuelve a intentar con NASA POWER
periodo = slice(f"{a0}-01-01", f"{a1}-12-01")
VAR_LLUVIA = catalogo.obtener_variable("precipitacion")

t_resumen, t_lluvia, t_sequia, t_humedad, t_estres, t_donde = st.tabs(
    ["Resumen", "Lluvia", "Sequía meteorológica", "Humedad del suelo", "Estrés hídrico del suelo", "¿Dónde?"])

# --- Resumen -------------------------------------------------------------------------------
with t_resumen:
    significa("resumen")
    with st.spinner("Calculando los resultados…"):
        r, res, con_ia = calcular_resumen(id_zona, a0, a1, _clave_gemini())
    t_ll = (r["lluvia"] or {}).get("tendencia")
    t_hu = (r["humedad_suelo"] or {}).get("tendencia")
    se, es = r["sequia_meteorologica"], r["estres_hidrico_suelo"]
    color_de = {"sube": "rojo", "baja": "verde", "no concluyente": "amarillo", "sin tendencia": "gris"}

    def tarjeta_tendencia(tema: str, t: dict | None, unidades: str, extra: str) -> dict:
        if t is None:
            return {"tema": tema, "icono": "–", "valor": "Sin datos suficientes", "texto": extra, "color": E.TINTA_SUAVE}
        v = E.VEREDICTO[color_de[t["veredicto"]]]
        return {"tema": tema, "icono": v["icono"], "valor": v["palabra"],
                "texto": f"{t['cambio_por_decada']:+.2f} {unidades} por década. {extra}", "color": v["tinta"]}

    tarjetas = [tarjeta_tendencia("Lluvia", t_ll, "mm/mes",
                                  f"En promedio, {r['lluvia']['promedio_anual_mm']} mm al año."
                                  if r["lluvia"]["promedio_anual_mm"] else ""),
                ]
    if se:
        tarjetas.append({"tema": "Sequía meteorológica (SPI-6)", "icono": "▼",
                         "valor": f"{se['meses_en_sequia']} de {se['meses_totales']} meses",
                         "texto": (f"Peor: {' – '.join(mes_texto(m) for m in se['peor_periodo'].split(' a '))} "
                                   f"({se['categoria_peor'].lower()})."
                                   if se["peor_periodo"] else "Sin rachas de sequía."),
                         "color": E.NIVEL["severo" if se["meses_en_sequia"] else "normal"]["color"]})
    tarjetas.append(tarjeta_tendencia("Humedad del suelo (raíces)", t_hu, "puntos de %", ""))
    if es:
        tarjetas.append({"tema": "Estrés hídrico del suelo", "icono": "▼",
                         "valor": f"{es['meses_en_deficit']} de {es['meses_totales']} meses",
                         "texto": f"{es['meses_en_deficit_ultimos_5_anios']} de ellos en los últimos 5 años.",
                         "color": E.NIVEL["moderado" if es["meses_en_deficit"] else "normal"]["color"]})
    st.markdown(E.tarjetas_html(tarjetas), unsafe_allow_html=True)
    origen = ("Escrito por Gemini a partir de los resultados que calculó la app (revisado: no trae cifras nuevas)."
              if con_ia else "Escrito con plantillas a partir de los resultados que calculó la app.")
    st.markdown(E.resumen_html(res, origen), unsafe_allow_html=True)
    limites("resumen")

# --- Lluvia --------------------------------------------------------------------------------
with t_lluvia:
    significa("lluvia")
    lluvia = lluvia_toda.loc[periodo]
    bloque_tendencia(lluvia, VAR_LLUVIA, a0, a1, "lluvia")

    st.markdown("##### Lluvia de cada año y de la temporada de lluvias (junio a octubre)")
    acum = indices.acumulados(lluvia)
    normal = indices.acumulados(lluvia_toda.loc["1991-01-01":"2020-12-01"])["anual_mm"].mean()
    fig = go.Figure([
        go.Bar(x=acum.index, y=acum["anual_mm"], name="Total del año", marker_color=E.TINTA_SUAVE,
               hovertemplate="%{x}: %{y:.0f} mm en el año<extra></extra>"),
        go.Bar(x=acum.index, y=acum["temporada_mm"], name="Temporada (jun–oct)", marker_color=E.MAS_AGUA,
               hovertemplate="%{x}: %{y:.0f} mm de junio a octubre<extra></extra>"),
    ])
    fig.add_hline(y=normal, line_dash="dash", line_color=E.TINTA, line_width=1.5,
                  annotation_text=f"Lo normal: {normal:.0f} mm al año (1991–2020)", annotation_position="top left",
                  annotation_font=dict(family=E.PILA_NUMEROS, size=12, color=E.TINTA))
    fig.update_layout(template=E.PLANTILLA, barmode="group", height=360, margin=dict(t=40, b=10, l=10, r=10),
                      xaxis_title="Año", yaxis_title="mm", legend=dict(orientation="h", y=1.14, x=0), bargap=0.25)
    st.plotly_chart(fig, width="stretch", config=E.CONFIG_GRAFICA, key="grafica_acumulados")
    incompletos = acum.index[~acum["completo"]].tolist()
    if incompletos:
        st.caption(f"Años sin barra: les falta algún mes ({', '.join(map(str, incompletos))}). No se rellenan con cero.")
    limites("lluvia")

# --- Sequía meteorológica ------------------------------------------------------------------
with t_sequia:
    significa("sequia")
    escala = st.radio("Índice", [3, 6], index=1, horizontal=True, key="escala_spi",
                      format_func=lambda e: f"SPI-{e} (últimos {e} meses)")
    try:
        spi_todo = indices.spi(lluvia_toda, escala)
        spi_p = spi_todo.loc[periodo]
        evidencias_indice(indices.resumen_indice(spi_p, "spi", idioma=IDIOMA), "spi", "sequia", "sequía")
        grafica_indice(spi_p.dropna(), "spi", f"SPI-{escala}", "spi")
    except ValueError as e:
        st.warning(f"No se puede calcular el SPI: {e}")
    limites("sequia")

# --- Humedad del suelo ---------------------------------------------------------------------
with t_humedad:
    significa("humedad")
    capa = st.radio("Capa del suelo", list(CAPAS), index=list(CAPAS).index(CAPA_INICIAL), horizontal=True,
                    format_func=CAPAS.get, key="capa")
    try:
        humedad, _ = cargar(capa, id_zona)
        var_capa = catalogo.obtener_variable(capa)
        st.caption(var_capa["definicion"])
        bloque_tendencia(humedad.loc[periodo], var_capa, a0, a1, "humedad")
    except Exception as e:
        st.error(f"No se pudo cargar la humedad de esa capa. ({type(e).__name__})")
    limites("humedad")

# --- Estrés hídrico del suelo --------------------------------------------------------------
with t_estres:
    significa("estres")
    capa_e = st.radio("Capa del suelo", list(CAPAS), index=list(CAPAS).index(CAPA_INICIAL), horizontal=True,
                      format_func=CAPAS.get, key="capa_estres")
    try:
        hum_e, _ = cargar(capa_e, id_zona)
        z = indices.estres_hidrico(hum_e).loc[periodo]
        evidencias_indice(indices.resumen_indice(z, "estres", idioma=IDIOMA), "estres", "estres", "déficit")
        grafica_indice(z.dropna(), "estres", "Anomalía estandarizada", "estres")
    except Exception as e:
        st.warning(f"No se puede calcular el estrés hídrico del suelo: {e}")
    limites("estres")

# --- ¿Dónde? -------------------------------------------------------------------------------
with t_donde:
    significa("donde")
    opciones = {"precipitacion": "Lluvia", **CAPAS}
    id_mapa = st.radio("Variable del mapa", list(opciones), horizontal=True, format_func=opciones.get, key="var_mapa")
    var_mapa = catalogo.obtener_variable(id_mapa)
    try:
        with st.spinner("Calculando la tendencia de cada celda…"):
            celdas_t = tendencias_celdas(id_mapa, id_zona, a0, a1)
    except Exception as e:
        st.error(f"No se pudieron cargar los datos de cada celda. ({type(e).__name__})")
        celdas_t = pd.DataFrame()
    if not celdas_t.empty:
        maximo = float(celdas_t["pendiente"].abs().max()) or 1.0
        contorno = region.contorno(id_zona)
        lats = [c["lat"] for c in region.celdas(id_zona)]
        lons = [c["lon"] for c in region.celdas(id_zona)]
        mapa = folium.Map(location=[(min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2],
                          zoom_start=8 if id_zona == "los-altos" else 9, tiles="OpenStreetMap", zoom_control=True,
                          scrollWheelZoom=False)
        for _, c in celdas_t.iterrows():
            v = E.VEREDICTO[c["color"]]
            segura = c["color"] in SEGURAS
            folium.Rectangle(
                bounds=[[c["lat"] - region.PASO_LAT / 2, c["lon"] - region.PASO_LON / 2],
                        [c["lat"] + region.PASO_LAT / 2, c["lon"] + region.PASO_LON / 2]],
                **(dict(color=E.TINTA, weight=4) if segura
                   else dict(color=E.TINTA_SUAVE, weight=1.5, dash_array="5 5")),
                fill=True, fill_color=E.color_cambio(c["pendiente"], maximo), fill_opacity=0.72,
                tooltip=(f"Celda {c['lat']:.2f}, {c['lon']:.3f} · {c['peso']:.0%} de la zona<br>"
                         f"{c['pendiente']:+.2f} {var_mapa['unidades']} por década · {v['icono']} {v['palabra']}<br>"
                         + ("<b>Tendencia segura</b>: las dos pruebas coinciden" if segura
                            else "Tendencia todavía no segura")),
            ).add_to(mapa)
        folium.GeoJson(
            contorno,
            style_function=lambda f: ({"color": E.TINTA, "weight": 3.5, "fill": False}
                                      if f["properties"]["tipo"] == "zona"
                                      else {"color": E.TINTA, "weight": 1, "fill": False, "dashArray": "3 4"}),
            tooltip=folium.GeoJsonTooltip(fields=["nombre"], labels=False),
        ).add_to(mapa)
        st.iframe(mapa.get_root().render(), height=520)  # HTML hecho por la app (folium), no de usuarios
        seguras = int(celdas_t["color"].isin(SEGURAS).sum())
        st.markdown(E.leyenda_mapa_html(maximo, var_mapa["unidades"], seguras, len(celdas_t)), unsafe_allow_html=True)

        tabla = celdas_t.assign(
            Celda=lambda d: d["lat"].map("{:.2f}".format) + ", " + d["lon"].map("{:.3f}".format),
            **{"% de la zona": lambda d: (d["peso"] * 100).round(1),
               f"Cambio por década ({var_mapa['unidades']})": lambda d: d["pendiente"].round(2),
               "Veredicto": lambda d: d["color"].map(lambda c: f"{E.VEREDICTO[c]['icono']} {E.VEREDICTO[c]['palabra']}"),
               "¿Tendencia segura?": lambda d: d["color"].map(lambda c: "Sí" if c in SEGURAS else "Todavía no")},
        )[["Celda", "% de la zona", f"Cambio por década ({var_mapa['unidades']})", "Veredicto", "¿Tendencia segura?"]]
        with st.expander("Ver la tabla de las celdas"):
            st.dataframe(tabla, hide_index=True, width="stretch")
    limites("donde")

# --- Fuentes del expediente ----------------------------------------------------------------
st.markdown(E.fuentes_html(CREDITOS), unsafe_allow_html=True)
