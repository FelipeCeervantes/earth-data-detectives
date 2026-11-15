"""Earth Data Detectives · Los Altos de Jalisco: app de Streamlit (en inglés, con botón ES para el equipo).

Ejecutar:  streamlit run app.py
Lo visual vive en src/estilo.py y los textos en src/textos.py (t(clave, idioma)); esta app solo usa las funciones
del contrato (tareas/contrato.md): region, catalogo, datos, indices, analisis y explicar.
"""

import os
import re
import warnings

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import catalogo, contraste, datos, explicar, indices, region
from src import estilo as E
from src import textos as T
from src.analisis import (anios_para_significancia, anomalias, cambio_total, mann_kendall, tendencia_ols,
                          veredicto)

st.set_page_config(page_title=T.t("pagina.titulo", "en"), page_icon=":material/water_drop:", layout="wide")
st.html(E.CSS)

ANIO_MIN, ANIO_MAX = 1981, 2024      # lo que hay en POWER mensual; se carga todo para calcular "lo normal"
PERIODO_INICIAL = (2001, 2024)
MIN_ANIOS = 10                       # con menos años, una tendencia es puro ruido
CAPAS = ("humedad_superficie", "humedad_raices", "humedad_perfil")
CAPA_INICIAL = "humedad_raices"
SEGURAS = ("rojo", "verde")          # veredicto "sube" o "baja": las dos pruebas coinciden
COLOR_DE = {"sube": "rojo", "baja": "verde", "no concluyente": "amarillo", "sin tendencia": "gris"}


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
def calcular_resumen(id_zona: str, a0: int, a1: int, idioma: str, _clave: str | None) -> tuple[dict, dict, bool]:
    """Resultados ya calculados (src.explicar) y su resumen en palabras: con Gemini si hay clave, si no, plantillas."""
    lluvia, _ = cargar("precipitacion", id_zona)
    humedad, _ = cargar(CAPA_INICIAL, id_zona)
    r = explicar.resultados(region.obtener_zona(id_zona, idioma)["nombre"], (a0, a1), lluvia, humedad,
                            capa=T.t("res.capa", idioma), idioma=idioma)
    con_ia = explicar.resumen_con_gemini(r, clave=_clave, idioma=idioma) if _clave else None
    return r, (con_ia or explicar.resumen_sin_ia(r, idioma=idioma)), con_ia is not None


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


# --- Idioma ----------------------------------------------------------------------------------
with st.sidebar:
    idioma = st.radio("Language · Idioma", T.IDIOMAS, horizontal=True, key="idioma",
                      format_func=lambda i: i.upper(),
                      help="The app is in English; ES is for the team to review. · La app va en inglés; ES es para "
                           "que el equipo revise.")


def tx(clave: str, **campos) -> str:
    """Texto de la interfaz en el idioma elegido."""
    return T.t(clave, idioma, **campos)


# --- Utilidades de presentación ------------------------------------------------------------
def numero(valor: float) -> str:
    return f"{valor:.1f}" if abs(valor) >= 10 else f"{valor:.2f}"


def p_texto(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def mes_texto(aaaa_mm: str) -> str:
    """'2011-01' -> 'Jan 2011' / 'ene 2011'."""
    anio, mes = aaaa_mm.split("-")
    return f"{T.mes_corto(int(mes), idioma)} {anio}"


def mes_largo(fecha: pd.Timestamp) -> str:
    return T.mes_largo(fecha.month, fecha.year, idioma)


def nombre_capa(id_capa: str) -> str:
    return tx(f"capa.{id_capa}")


def significa(clave: str) -> None:
    no_es = tx(f"no_es.{clave}") if T.tiene(f"no_es.{clave}", idioma) else None
    st.markdown(E.significa_html(tx(f"significa.{clave}"), no_es, idioma), unsafe_allow_html=True)


def limites(clave: str) -> None:
    st.markdown(E.limites_html(tx("fuente_power"), tx(f"limites.{clave}"), idioma), unsafe_allow_html=True)


def evidencias(lista: list[tuple[str, str, str, str]], clave: str) -> None:
    """Fila de tarjetas EVIDENCE 01…: [(título, valor, nota, ayuda)]."""
    for i, (col, (titulo, valor, nota, ayuda)) in enumerate(zip(st.columns(len(lista)), lista), start=1):
        with col.container(border=True, key=f"evidencia_{clave}_{i}"):
            st.metric(tx("ev.etiqueta", i=i, titulo=titulo), valor, help=ayuda or None)
            st.caption(nota)


def bloque_tendencia(serie: pd.Series, var: dict, a0: int, a1: int, clave: str) -> None:
    """Veredicto como sello, evidencias, gráfica (real o anomalías) con la tendencia y descarga CSV."""
    u = var["unidades"]
    anom = anomalias(serie)
    try:
        ols, mk = tendencia_ols(anom), mann_kendall(anom, metodo="hamed_rao")
    except ValueError as e:
        st.warning(tx("error.tendencia", e=e))
        return
    v = veredicto(ols, mk, u, idioma=idioma)
    color = E.VEREDICTO[v["color"]]["tinta"]
    st.markdown(E.sello_html(v["color"], v["texto"], idioma), unsafe_allow_html=True)
    faltan = anios_para_significancia(ols)
    if faltan:
        st.markdown(E.faltan_html(max(1, round(faltan)), idioma), unsafe_allow_html=True)

    total = cambio_total(serie, ols)
    anios = f"{total['anios']:.0f}"
    valor_total = f"{total['cambio']:+.2f} {u}"
    if total["porcentaje"] is not None and var["tipo"] == "lluvia":  # en humedad (ya en %) confundiría
        valor_total += f" ({total['porcentaje']:+.1f} %)"
    evidencias([
        (tx("ev.cambio.titulo"), f"{ols['pendiente_decada']:+.2f} {u}",
         tx("ev.cambio.nota", lo=f"{ols['ic_bajo']:+.2f}", hi=f"{ols['ic_alto']:+.2f}"),
         tx("ev.cambio.ayuda", sen=f"{mk['pendiente_sen_decada']:+.2f}", u=u)),
        (tx("ev.total.titulo", n=anios), valor_total, tx("ev.total.nota"), tx("ev.total.ayuda")),
        (tx("ev.recta.titulo"), p_texto(ols["p_valor"]), tx("ev.recta.nota"), tx("ev.recta.ayuda") + tx("ayuda.p")),
        (tx("ev.mk.titulo"), p_texto(mk["p_valor"]), tx("ev.mk.nota"), tx("ev.mk.ayuda") + tx("ayuda.p")),
    ], clave)

    vista = st.radio(tx("graf.ver"), ["reales", "anomalias"], horizontal=True, key=f"vista_{clave}",
                     format_func=lambda o: tx(f"graf.{o}"), help=tx("graf.ver.ayuda"))
    s = (serie if vista == "reales" else anom).dropna()
    t = np.asarray(((s.index.year + (s.index.month - 1) / 12) - s.index.year[0]) / 10)
    tc, yc = t.mean(), s.mean()
    recta = yc + ols["pendiente_decada"] * (t - tc)
    lo, hi = yc + ols["ic_bajo"] * (t - tc), yc + ols["ic_alto"] * (t - tc)
    fig = go.Figure([
        go.Scatter(x=s.index, y=s, name=tx("graf.valor_mensual" if vista == "reales" else "graf.anomalia_mensual"),
                   line=E.SERIE_MENSUAL, hovertemplate=f"%{{y:.1f}} {u}"),
        go.Scatter(x=s.index, y=np.maximum(lo, hi), line=dict(width=0), showlegend=False, hoverinfo="skip"),
        go.Scatter(x=s.index, y=np.minimum(lo, hi), fill="tonexty", fillcolor=E.rgba(color, 0.16),
                   line=dict(width=0), name=tx("graf.margen"), hoverinfo="skip"),
        go.Scatter(x=s.index, y=recta, name=tx("graf.tendencia"), line=dict(color=color, width=4),
                   hovertemplate=f"%{{y:.1f}} {u}"),
    ])
    fig.update_layout(
        template=E.PLANTILLA, height=420, margin=dict(t=40, b=10, l=10, r=10), hovermode="x unified",
        xaxis_title=tx("graf.anio"), yaxis_title=tx("graf.eje_valor" if vista == "reales" else "graf.eje_anomalia", u=u),
        xaxis_hoverformat=E.FORMATO_MES, legend=dict(orientation="h", y=1.14, x=0),
        annotations=[
            E.anotacion(s.index[0], recta[0], f"{s.index[0].year}: {numero(recta[0])} {u}", color, derecha=False),
            E.anotacion(s.index[-1], recta[-1], f"{s.index[-1].year}: {numero(recta[-1])} {u}<br><b>"
                        + tx("graf.anot_total", cambio=f"{total['cambio']:+.2f}", u=u, n=anios) + "</b>",
                        color, derecha=True),
        ],
    )
    st.plotly_chart(fig, width="stretch", config=E.config_grafica(idioma), key=f"grafica_{clave}")
    if vista == "anomalias":
        st.caption(tx("graf.nota_anomalia", a0=a0, a1=a1))
    tabla = pd.DataFrame({tx("csv.fecha"): serie.index.strftime("%Y-%m"), var["id"]: serie.values,
                          tx("csv.anomalia"): anom.values})
    st.download_button(tx("descargar", nombre=var["nombre"].lower()), tabla.to_csv(index=False).encode("utf-8"),
                       file_name=f"{var['id']}_{id_zona}_{a0}_{a1}.csv", mime="text/csv",
                       icon=":material/download:", key=f"descarga_{clave}")


def grafica_indice(serie: pd.Series, indice: str, titulo_y: str, clave: str) -> None:
    """Barras mensuales del índice coloreadas por categoría, con bandas de fondo moderada/severa/extrema."""
    cats = [indices.categoria(float(v), indice, idioma=idioma) for v in serie]
    un_mes = 27 * 24 * 3600 * 1000  # ancho de cada barra, en milisegundos (eje de fechas)
    fig = go.Figure()
    for desde, hasta, nivel, _ in E.BANDAS:
        fig.add_hrect(y0=desde, y1=hasta, fillcolor=E.rgba(E.NIVEL[nivel]["color"], 0.10), line_width=0)
        fig.add_annotation(xref="paper", x=1.01, xanchor="left", y=(max(desde, -3.5) + hasta) / 2,
                           text=tx(f"banda.{nivel}"), showarrow=False,
                           font=dict(family=E.PILA_NUMEROS, size=11, color=E.NIVEL[nivel]["color"]))
    for nivel in ("humedo", "normal", "moderado", "severo", "extremo"):
        mascara = [c["nivel"] == nivel for c in cats]
        if not any(mascara):
            continue
        sub = serie[mascara]
        nombre = indices.NOMBRES[idioma][indice][nivel]
        fig.add_bar(x=sub.index, y=sub.values, name=f"{E.NIVEL[nivel]['icono']} {nombre}", width=un_mes,
                    marker=dict(color=E.NIVEL[nivel]["color"], line=dict(width=0)),
                    hovertemplate=f"%{{y:+.2f}} · {nombre}<extra></extra>")
    fig.update_layout(template=E.PLANTILLA, height=380, margin=dict(t=40, b=10, l=10, r=70), barmode="overlay",
                      bargap=0, xaxis_title=tx("graf.anio"), yaxis_title=titulo_y, xaxis_hoverformat=E.FORMATO_MES,
                      yaxis=dict(range=[-3.5, 3.5], zeroline=True, zerolinewidth=1.5),
                      xaxis=dict(range=[serie.index[0] - pd.DateOffset(months=1),
                                        serie.index[-1] + pd.DateOffset(months=1)]),
                      legend=dict(orientation="h", y=1.14, x=0), hovermode="x")
    st.plotly_chart(fig, width="stretch", config=E.config_grafica(idioma), key=f"grafica_{clave}")


def evidencias_indice(res: dict, clave: str, palabra: str) -> None:
    peor = res["peor_periodo"]
    ultimo = pd.Timestamp(res["ultimo_mes"] + "-01")
    evidencias([
        (tx("ind.meses.titulo", palabra=palabra), f"{res['meses_en_deficit']} / {res['meses_totales']}",
         tx("ind.meses.nota", pct=f"{res['meses_en_deficit'] / max(res['meses_totales'], 1):.0%}"), ""),
        (tx("ind.ultimos.titulo"), tx("ind.ultimos.valor", n=res["meses_en_deficit_ultimos"], palabra=palabra),
         tx("ind.ultimos.nota", desde=mes_largo(ultimo - pd.DateOffset(years=5, months=-1)), hasta=mes_largo(ultimo)),
         ""),
        (tx("ind.peor.titulo"), f"{mes_texto(peor[0])} – {mes_texto(peor[1])}" if peor else tx("ind.peor.ninguno"),
         res["categoria_peor"] or tx("ind.peor.sin"), tx("ind.peor.ayuda")),
        (tx("ind.ultimo.titulo"), f"{res['valor_ultimo']:+.2f}", f"{mes_texto(res['ultimo_mes'])}: "
         f"{res['categoria_ultimo']}.", ""),
    ], clave)


# --- Panel del detective -------------------------------------------------------------------
st.markdown(E.marca_html(idioma), unsafe_allow_html=True)
with st.sidebar:
    st.markdown(E.panel_html(idioma), unsafe_allow_html=True)
    id_zona = st.selectbox(tx("panel.donde"), list(region.ZONAS), key="zona",
                           format_func=lambda z: region.obtener_zona(z, idioma)["nombre"])
    zona = region.obtener_zona(id_zona, idioma)
    st.caption(tx("panel.municipios", n=len(zona["municipios"]), lista=", ".join(zona["municipios"])))
    a0, a1 = st.slider(tx("panel.periodo"), ANIO_MIN, ANIO_MAX, PERIODO_INICIAL, key="periodo")
    st.caption(tx("panel.normal"))

lugar = tx("lugar.los-altos") if id_zona == "los-altos" else zona["nombre"]
st.markdown(E.caso_html(tx("caso.numero", lugar=lugar, a0=a0, a1=a1), tx("caso.pregunta", lugar=lugar),
                        tx("caso.nota"), idioma), unsafe_allow_html=True)

if a1 - a0 + 1 < MIN_ANIOS:
    st.error(tx("error.periodo_corto", n=MIN_ANIOS))
    st.stop()

try:
    with st.spinner(tx("spinner.descarga")):
        lluvia_toda, avisos_ll = cargar("precipitacion", id_zona)
        humedad_toda, avisos_hu = cargar(CAPA_INICIAL, id_zona)
except ValueError as e:
    st.error(tx("error.entrada", e=e))
    st.stop()
except Exception as e:  # sin red y sin respaldo, servidor caído: aviso en vez de romper la app
    st.error(tx("error.descarga", e=type(e).__name__))
    st.stop()

if any("Sin conexión" in a for a in avisos_ll + avisos_hu):
    st.warning(tx("aviso.sin_conexion"), icon=":material/inventory_2:")
    cargar.clear()  # la próxima vez se vuelve a intentar con NASA POWER
periodo = slice(f"{a0}-01-01", f"{a1}-12-01")
VAR_LLUVIA = catalogo.obtener_variable("precipitacion", idioma)

t_resumen, t_lluvia, t_sequia, t_humedad, t_estres, t_donde = st.tabs(
    [tx(f"tab.{k}") for k in ("resumen", "lluvia", "sequia", "humedad", "estres", "donde")])

# --- Resumen -------------------------------------------------------------------------------
with t_resumen:
    significa("resumen")
    with st.spinner(tx("spinner.resultados")):
        r, res, con_ia = calcular_resumen(id_zona, a0, a1, idioma, _clave_gemini())
    t_ll = (r["lluvia"] or {}).get("tendencia")
    t_hu = (r["humedad_suelo"] or {}).get("tendencia")
    se, es = r["sequia_meteorologica"], r["estres_hidrico_suelo"]

    def tarjeta_tendencia(tema: str, t: dict | None, unidades: str, extra: str) -> dict:
        if t is None:
            return {"tema": tema, "icono": "–", "valor": tx("res.sin_datos"), "texto": extra, "color": E.TINTA_SUAVE}
        color = COLOR_DE[t["veredicto"]]
        cambio = f"{t['cambio_por_decada']:+.2f}"
        texto = f"{tx('res.por_decada', v=cambio, u=unidades)} {extra}".strip()
        return {"tema": tema, "icono": E.VEREDICTO[color]["icono"], "valor": E.palabra(color, idioma),
                "texto": texto, "color": E.VEREDICTO[color]["tinta"]}

    promedio = r["lluvia"]["promedio_anual_mm"]
    tarjetas = [tarjeta_tendencia(tx("res.lluvia"), t_ll, tx("res.u_lluvia"),
                                  tx("res.promedio", mm=promedio) if promedio else "")]
    if se:
        peor = (" – ".join(mes_texto(m) for m in re.split(r"\s(?:a|to)\s", se["peor_periodo"]))
                if se["peor_periodo"] else None)
        tarjetas.append({"tema": tx("res.sequia"), "icono": "▼",
                         "valor": tx("res.meses", n=se["meses_en_sequia"], total=se["meses_totales"]),
                         "texto": tx("res.peor", periodo=peor, cat=se["categoria_peor"].lower()) if peor
                         else tx("res.sin_rachas"),
                         "color": E.NIVEL["severo" if se["meses_en_sequia"] else "normal"]["color"]})
    tarjetas.append(tarjeta_tendencia(tx("res.humedad"), t_hu, tx("res.u_humedad"), ""))
    if es:
        tarjetas.append({"tema": tx("res.estres"), "icono": "▼",
                         "valor": tx("res.meses", n=es["meses_en_deficit"], total=es["meses_totales"]),
                         "texto": tx("res.ultimos", n=es["meses_en_deficit_ultimos_5_anios"]),
                         "color": E.NIVEL["moderado" if es["meses_en_deficit"] else "normal"]["color"]})
    st.markdown(E.tarjetas_html(tarjetas), unsafe_allow_html=True)
    origen = tx("res.origen_ia" if con_ia else "res.origen_plantillas")
    st.markdown(E.resumen_html(res, origen, idioma), unsafe_allow_html=True)
    limites("resumen")

# --- Lluvia --------------------------------------------------------------------------------
with t_lluvia:
    significa("lluvia")
    lluvia = lluvia_toda.loc[periodo]
    bloque_tendencia(lluvia, VAR_LLUVIA, a0, a1, "lluvia")

    st.markdown(f"##### {tx('lluvia.acum.titulo')}")
    acum = indices.acumulados(lluvia)
    normal = indices.acumulados(lluvia_toda.loc["1991-01-01":"2020-12-01"])["anual_mm"].mean()
    fig = go.Figure([
        go.Bar(x=acum.index, y=acum["anual_mm"], name=tx("lluvia.acum.anual"), marker_color=E.TINTA_SUAVE,
               hovertemplate=tx("lluvia.acum.hover_anual") + "<extra></extra>"),
        go.Bar(x=acum.index, y=acum["temporada_mm"], name=tx("lluvia.acum.temporada"), marker_color=E.MAS_AGUA,
               hovertemplate=tx("lluvia.acum.hover_temp") + "<extra></extra>"),
    ])
    fig.add_hline(y=normal, line_dash="dash", line_color=E.TINTA, line_width=1.5,
                  annotation_text=tx("lluvia.acum.normal", mm=f"{normal:.0f}"), annotation_position="top left",
                  annotation_font=dict(family=E.PILA_NUMEROS, size=12, color=E.TINTA))
    fig.update_layout(template=E.PLANTILLA, barmode="group", height=360, margin=dict(t=40, b=10, l=10, r=10),
                      xaxis_title=tx("graf.anio"), yaxis_title="mm", legend=dict(orientation="h", y=1.14, x=0),
                      bargap=0.25)
    st.plotly_chart(fig, width="stretch", config=E.config_grafica(idioma), key="grafica_acumulados")
    incompletos = acum.index[~acum["completo"]].tolist()
    if incompletos:
        st.caption(tx("lluvia.acum.incompletos", lista=", ".join(map(str, incompletos))))
    limites("lluvia")

    st.markdown(f"##### {tx('est.titulo')}")
    st.caption(tx("est.intro"))
    est_zona = contraste.estaciones(id_zona)
    comp_est = contraste.comparar_lluvia(lluvia, contraste.lluvia_estaciones(id_zona).loc[periodo])
    if comp_est is None:
        st.info(tx("est.sin"))
    else:
        evidencias([
            (tx("est.n.titulo"), str(len(est_zona)), tx("est.n.nota"), ""),
            (tx("est.r.titulo"), f"{comp_est['r_anual']:.2f}", tx("est.r.nota", n=comp_est["anios"]),
             tx("est.r.ayuda")),
            (tx("est.dif.titulo"), f"{comp_est['diferencia_pct']:+.0f} %", tx("est.dif.nota"), ""),
        ], "estaciones")
        anual = comp_est["anual"]
        fig = go.Figure([
            go.Scatter(x=anual.index, y=anual["estaciones"], name=tx("est.graf.est"), mode="lines+markers",
                       line=dict(color=E.TINTA, width=2, dash="dot"), hovertemplate="%{y:.0f} mm<extra></extra>"),
            go.Scatter(x=anual.index, y=anual["power"], name=tx("est.graf.power"), mode="lines+markers",
                       line=dict(color=E.MAS_AGUA, width=3), hovertemplate="%{y:.0f} mm<extra></extra>"),
        ])
        fig.update_layout(template=E.PLANTILLA, height=340, margin=dict(t=40, b=10, l=10, r=10),
                          xaxis_title=tx("graf.anio"), yaxis_title=tx("est.graf.eje"),
                          legend=dict(orientation="h", y=1.14, x=0), hovermode="x unified")
        st.plotly_chart(fig, width="stretch", config=E.config_grafica(idioma), key="grafica_estaciones")
    st.markdown(E.limites_html(tx("est.fuente", n=len(est_zona)), tx("est.limite"), idioma), unsafe_allow_html=True)

# --- Sequía meteorológica ------------------------------------------------------------------
with t_sequia:
    significa("sequia")
    escala = st.radio(tx("sequia.indice"), [3, 6], index=1, horizontal=True, key="escala_spi",
                      format_func=lambda e: tx("sequia.formato", e=e))
    try:
        spi_p = indices.spi(lluvia_toda, escala).loc[periodo]
        evidencias_indice(indices.resumen_indice(spi_p, "spi", idioma=idioma), "sequia", tx("palabra.sequia"))
        grafica_indice(spi_p.dropna(), "spi", f"SPI-{escala}", "spi")
    except ValueError as e:
        st.warning(tx("error.spi", e=e))
        spi_p = None
    limites("sequia")

    st.markdown(f"##### {tx('msm.titulo')}")
    st.caption(tx("msm.intro"))
    msm = contraste.monitor(id_zona)
    msm_p = msm.loc[periodo]
    comp_msm = contraste.comparar_sequia(spi_p, msm_p["fraccion_sequia"]) if spi_p is not None else None
    if comp_msm is None:
        st.info(tx("msm.sin"))
    else:
        ult = msm.iloc[-1]
        if comp_msm["meses_spi"]:
            conf = (tx("msm.conf.valor", c=comp_msm["confirmados"], n=comp_msm["meses_spi"]),
                    tx("msm.conf.nota", pct=f"{comp_msm['pct_confirmados']:.0f} %",
                       desde=mes_texto(f"{comp_msm['desde']:%Y-%m}"), hasta=mes_texto(f"{comp_msm['hasta']:%Y-%m}")))
        else:
            conf = ("–", tx("msm.conf.ninguno"))
        evidencias([
            (tx("msm.conf.titulo"), *conf, ""),
            (tx("msm.of.titulo"), f"{comp_msm['meses_oficial']} / {comp_msm['meses']}", tx("msm.of.nota"), ""),
            (tx("msm.ult.titulo"), tx("msm.ult.valor", n=int(ult[list(contraste.EN_SEQUIA)].sum()),
                                      total=int(ult["total"])),
             tx("msm.ult.nota", fecha=mes_largo(msm.index[-1]), d0=int(ult["D0"])), ""),
        ], "monitor")
        colores = (E.AMBAR, E.NIVEL["moderado"]["color"], E.NIVEL["severo"]["color"], E.NIVEL["extremo"]["color"],
                   E.TINTA)
        fig = go.Figure()
        for cat, color in zip(contraste.CATEGORIAS, colores):
            fig.add_bar(x=msm_p.index, y=msm_p[cat], name=tx(f"msm.{cat}"), width=27 * 24 * 3600 * 1000,
                        marker=dict(color=color, line=dict(width=0)),
                        hovertemplate=f"%{{y}} · {tx(f'msm.{cat}')}<extra></extra>")
        fig.update_layout(template=E.PLANTILLA, barmode="stack", bargap=0, height=340,
                          margin=dict(t=40, b=10, l=10, r=10), xaxis_title=tx("graf.anio"),
                          yaxis=dict(title=tx("msm.eje"), range=[0, int(msm["total"].iloc[0])]),
                          xaxis_hoverformat=E.FORMATO_MES, legend=dict(orientation="h", y=1.18, x=0),
                          hovermode="x unified")
        st.plotly_chart(fig, width="stretch", config=E.config_grafica(idioma), key="grafica_monitor")
    st.markdown(E.limites_html(tx("msm.fuente"), tx("msm.limite"), idioma), unsafe_allow_html=True)

# --- Humedad del suelo ---------------------------------------------------------------------
with t_humedad:
    significa("humedad")
    capa = st.radio(tx("humedad.capa"), CAPAS, index=CAPAS.index(CAPA_INICIAL), horizontal=True,
                    format_func=nombre_capa, key="capa")
    try:
        humedad, _ = cargar(capa, id_zona)
        var_capa = catalogo.obtener_variable(capa, idioma)
        st.caption(var_capa["definicion"])
        bloque_tendencia(humedad.loc[periodo], var_capa, a0, a1, "humedad")
    except Exception as e:
        st.error(tx("error.capa", e=type(e).__name__))
    limites("humedad")

# --- Estrés hídrico del suelo --------------------------------------------------------------
with t_estres:
    significa("estres")
    capa_e = st.radio(tx("humedad.capa"), CAPAS, index=CAPAS.index(CAPA_INICIAL), horizontal=True,
                      format_func=nombre_capa, key="capa_estres")
    try:
        hum_e, _ = cargar(capa_e, id_zona)
        z = indices.estres_hidrico(hum_e).loc[periodo]
        evidencias_indice(indices.resumen_indice(z, "estres", idioma=idioma), "estres", tx("palabra.deficit"))
        grafica_indice(z.dropna(), "estres", tx("estres.eje"), "estres")
    except Exception as e:
        st.warning(tx("error.estres", e=e))
    limites("estres")

# --- ¿Dónde? -------------------------------------------------------------------------------
with t_donde:
    significa("donde")
    opciones = ("precipitacion", *CAPAS)
    id_mapa = st.radio(tx("donde.variable"), opciones, horizontal=True, key="var_mapa",
                       format_func=lambda o: tx("donde.lluvia") if o == "precipitacion" else nombre_capa(o))
    var_mapa = catalogo.obtener_variable(id_mapa, idioma)
    u_mapa = var_mapa["unidades"]
    try:
        with st.spinner(tx("spinner.celdas")):
            celdas_t = tendencias_celdas(id_mapa, id_zona, a0, a1)
    except Exception as e:
        st.error(tx("error.celdas", e=type(e).__name__))
        celdas_t = pd.DataFrame()
    if not celdas_t.empty:
        maximo = float(celdas_t["pendiente"].abs().max()) or 1.0
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
                tooltip=(tx("donde.celda", lat=f"{c['lat']:.2f}", lon=f"{c['lon']:.3f}", peso=f"{c['peso']:.0%}")
                         + "<br>" + tx("donde.por_decada", pend=f"{c['pendiente']:+.2f}", u=u_mapa, icono=v["icono"],
                                       palabra=E.palabra(c["color"], idioma))
                         + "<br>" + tx("donde.segura" if segura else "donde.no_segura")),
            ).add_to(mapa)
        folium.GeoJson(
            region.contorno(id_zona),
            style_function=lambda f: ({"color": E.TINTA, "weight": 3.5, "fill": False}
                                      if f["properties"]["tipo"] == "zona"
                                      else {"color": E.TINTA, "weight": 1, "fill": False, "dashArray": "3 4"}),
            tooltip=folium.GeoJsonTooltip(fields=["nombre"], labels=False),
        ).add_to(mapa)
        for _, s in contraste.estaciones(id_zona).iterrows():
            folium.CircleMarker([s["lat"], s["lon"]], radius=5, color=E.TINTA, weight=1.5, fill=True,
                                fill_color="#FFFFFF", fill_opacity=0.95,
                                tooltip=tx("donde.estacion", nombre=s["nombre"], municipio=s["municipio"])).add_to(mapa)
        st.iframe(mapa.get_root().render(), height=520)  # HTML hecho por la app (folium), no de usuarios
        seguras = int(celdas_t["color"].isin(SEGURAS).sum())
        st.markdown(E.leyenda_mapa_html(maximo, u_mapa, seguras, len(celdas_t), idioma), unsafe_allow_html=True)
        st.caption(tx("donde.puntos"))

        col_cambio = tx("tabla.cambio", u=u_mapa)
        tabla = pd.DataFrame({
            tx("tabla.celda"): celdas_t["lat"].map("{:.2f}".format) + ", " + celdas_t["lon"].map("{:.3f}".format),
            tx("tabla.zona"): (celdas_t["peso"] * 100).round(1),
            col_cambio: celdas_t["pendiente"].round(2),
            tx("tabla.veredicto"): celdas_t["color"].map(lambda c: f"{E.VEREDICTO[c]['icono']} {E.palabra(c, idioma)}"),
            tx("tabla.segura"): celdas_t["color"].map(lambda c: tx("tabla.si") if c in SEGURAS else tx("tabla.no")),
        })
        with st.expander(tx("tabla.ver")):
            st.dataframe(tabla, hide_index=True, width="stretch")
    limites("donde")

# --- Fuentes del expediente ----------------------------------------------------------------
st.markdown(E.fuentes_html(tx("creditos"), idioma), unsafe_allow_html=True)
