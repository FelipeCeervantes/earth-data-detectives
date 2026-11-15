"""Earth Data Detectives · Los Altos de Jalisco: app de Streamlit (en inglés, con botón ES para el equipo).

Ejecutar:  streamlit run app.py
Tres secciones (Panorama, Lluvia y sequía, Agua del suelo); en cada una va primero la gráfica o el mapa y abajo
qué significa. Lo visual vive en src/estilo.py (y el fondo 3D en src/fondo.py) y los textos en src/textos.py
(t(clave, idioma)); esta app solo usa las funciones del contrato (tareas/contrato.md): region, catalogo, datos,
indices, analisis, explicar y contraste.
"""

import os
import re
import warnings

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from src import catalogo, contraste, datos, explicar, fondo, indices, region
from src import estilo as E
from src import textos as T
from src.analisis import (anios_para_significancia, anomalias, cambio_total, mann_kendall, tendencia_ols,
                          veredicto)

st.set_page_config(page_title=T.t("pagina.titulo", "en"), page_icon=":material/water_drop:", layout="wide",
                   initial_sidebar_state="collapsed")
st.html(E.CSS)
if fondo.html():
    with st.container(key="fondo3d"):
        st.iframe(fondo.html(), height=1)  # HTML hecho por la app (src/fondo.py); la CSS lo pone de fondo

ANIO_MIN, ANIO_MAX = 1981, 2024      # lo que hay en POWER mensual; se carga todo para calcular "lo normal"
PERIODO_INICIAL = (2001, 2024)
MIN_ANIOS = 10                       # con menos años, una tendencia es puro ruido
CAPAS = ("humedad_superficie", "humedad_raices", "humedad_perfil")
CAPA_INICIAL = "humedad_raices"
VISTAS = ("resumen", "lluvia", "suelo")
ICONO_VISTA = {"resumen": ":material/travel_explore:", "lluvia": ":material/rainy:", "suelo": ":material/grass:"}
SEGURAS = ("rojo", "verde")          # veredicto "sube" o "baja": las dos pruebas coinciden
COLOR_DE = {"sube": "rojo", "baja": "verde", "no concluyente": "amarillo", "sin tendencia": "gris"}
UN_MES = 27 * 24 * 3600 * 1000       # ancho de una barra mensual, en milisegundos (eje de fechas)


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


# --- Encabezado e idioma -------------------------------------------------------------------
# El botón EN/ES va hasta abajo (es solo para que el equipo revise); aquí solo se lee lo elegido.
idioma = st.session_state.get("idioma") or T.IDIOMA_INICIAL
cab = st.container()


def tx(clave: str, **campos) -> str:
    """Texto de la interfaz en el idioma elegido."""
    return T.t(clave, idioma, **campos)


def pie() -> None:
    """Fuentes y el botón EN/ES (se dibuja en cada corrida, también antes de un st.stop, para no perder el idioma)."""
    st.markdown(E.fuentes_html(tx("creditos"), idioma), unsafe_allow_html=True)
    st.segmented_control("Language · Idioma", T.IDIOMAS, key="idioma", default=T.IDIOMA_INICIAL, required=True,
                         format_func=str.upper, help="The app is in English; ES is for the team to review. · La app "
                                                     "va en inglés; ES es para que el equipo revise.")


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


def seccion(clave: str) -> None:
    st.markdown(E.seccion_html(tx(clave)), unsafe_allow_html=True)


def significa(clave: str) -> None:
    """"¿Qué significa?": va debajo de la gráfica que explica."""
    no_es = tx(f"no_es.{clave}") if T.tiene(f"no_es.{clave}", idioma) else None
    st.markdown(E.significa_html(tx(f"significa.{clave}"), no_es, idioma), unsafe_allow_html=True)


def explica(texto: str) -> None:
    st.markdown(E.significa_html(texto, None, idioma), unsafe_allow_html=True)


def limites(*partes: str) -> None:
    st.markdown(E.limites_html(list(partes), idioma), unsafe_allow_html=True)


def grafica(fig: go.Figure, clave: str, alto: int) -> None:
    fig.update_layout(template=E.PLANTILLA, height=alto, margin=dict(l=58, r=12, t=14, b=10))
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True, title_standoff=8)
    # theme=None: sin el tema de Streamlit, que ponía fondo oscuro y recortaba la leyenda de abajo
    st.plotly_chart(fig, width="stretch", config=E.config_grafica(idioma), key=f"grafica_{clave}", theme=None)


def evidencias(lista: list[tuple[str, str, str, str]], clave: str) -> None:
    """Fila de tarjetas EVIDENCE 01…: [(título, valor, nota, ayuda)]."""
    for i, (col, (titulo, valor, nota, ayuda)) in enumerate(zip(st.columns(len(lista)), lista), start=1):
        with col.container(border=True, key=f"evidencia_{clave}_{i}"):
            st.metric(tx("ev.etiqueta", i=i, titulo=titulo), valor, help=ayuda or None)
            st.caption(nota)


def bloque_tendencia(serie: pd.Series, var: dict, a0: int, a1: int, clave: str) -> None:
    """Gráfica (real o anomalías) con la tendencia; abajo el veredicto, las evidencias y la descarga CSV."""
    u = var["unidades"]
    anom = anomalias(serie)
    try:
        ols, mk = tendencia_ols(anom), mann_kendall(anom, metodo="hamed_rao")
    except ValueError as e:
        st.warning(tx("error.tendencia", e=e))
        return
    v = veredicto(ols, mk, u, idioma=idioma)
    color = E.VEREDICTO[v["color"]]["tinta"]
    total = cambio_total(serie, ols)
    anios = f"{total['anios']:.0f}"

    vista = st.segmented_control(tx("graf.ver"), ["reales", "anomalias"], key=f"vista_{clave}", default="reales",
                                 required=True, format_func=lambda o: tx(f"graf.{o}"), help=tx("graf.ver.ayuda"))
    s = (serie if vista == "reales" else anom).dropna()
    t = np.asarray(((s.index.year + (s.index.month - 1) / 12) - s.index.year[0]) / 10)
    tc, yc = t.mean(), s.mean()
    recta = yc + ols["pendiente_decada"] * (t - tc)
    lo, hi = yc + ols["ic_bajo"] * (t - tc), yc + ols["ic_alto"] * (t - tc)
    fig = go.Figure([
        go.Scatter(x=s.index, y=s, name=tx("graf.valor_mensual" if vista == "reales" else "graf.anomalia_mensual"),
                   line=E.SERIE_MENSUAL, hovertemplate=f"%{{y:.1f}} {u}"),
        go.Scatter(x=s.index, y=np.maximum(lo, hi), line=dict(width=0), showlegend=False, hoverinfo="skip"),
        go.Scatter(x=s.index, y=np.minimum(lo, hi), fill="tonexty", fillcolor=E.rgba(color, 0.18),
                   line=dict(width=0), name=tx("graf.margen"), hoverinfo="skip"),
        go.Scatter(x=s.index, y=recta, name=tx("graf.tendencia"), line=dict(color=color, width=4),
                   hovertemplate=f"%{{y:.1f}} {u}"),
    ])
    fig.update_layout(hovermode="x unified", xaxis_hoverformat=E.FORMATO_MES,
                      yaxis_title=tx("graf.eje_valor" if vista == "reales" else "graf.eje_anomalia", u=u))
    grafica(fig, clave, 400)
    st.caption(tx("graf.recta", v0=numero(recta[0]), v1=numero(recta[-1]), a0=s.index[0].year, a1=s.index[-1].year,
                  cambio=f"{total['cambio']:+.2f}", u=u, n=anios)
               + (" " + tx("graf.nota_anomalia", a0=a0, a1=a1) if vista == "anomalias" else ""))

    st.markdown(E.sello_html(v["color"], v["texto"], idioma), unsafe_allow_html=True)
    faltan = anios_para_significancia(ols)
    if faltan:
        st.markdown(E.faltan_html(max(1, round(faltan)), idioma), unsafe_allow_html=True)
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
    tabla = pd.DataFrame({tx("csv.fecha"): serie.index.strftime("%Y-%m"), var["id"]: serie.values,
                          tx("csv.anomalia"): anom.values})
    st.download_button(tx("descargar", nombre=var["nombre"].lower()), tabla.to_csv(index=False).encode("utf-8"),
                       file_name=f"{var['id']}_{id_zona}_{a0}_{a1}.csv", mime="text/csv",
                       icon=":material/download:", key=f"descarga_{clave}")


def grafica_indice(serie: pd.Series, indice: str, titulo_y: str, clave: str) -> None:
    """Barras mensuales del índice coloreadas por categoría, con bandas de fondo moderada/severa/extrema."""
    cats = [indices.categoria(float(v), indice, idioma=idioma) for v in serie]
    fig = go.Figure()
    for desde, hasta, nivel, _ in E.BANDAS:
        # Bandas de fondo sin etiqueta encima: la leyenda ya nombra cada nivel (en el celular se cortaban)
        fig.add_hrect(y0=desde, y1=hasta, fillcolor=E.rgba(E.NIVEL[nivel]["color"], 0.10), line_width=0)
    for nivel in ("humedo", "normal", "moderado", "severo", "extremo"):
        mascara = [c["nivel"] == nivel for c in cats]
        if not any(mascara):
            continue
        sub = serie[mascara]
        nombre = indices.NOMBRES[idioma][indice][nivel]
        fig.add_bar(x=sub.index, y=sub.values, name=f"{E.NIVEL[nivel]['icono']} {nombre}", width=UN_MES,
                    marker=dict(color=E.NIVEL[nivel]["color"], line=dict(width=0)),
                    hovertemplate=f"%{{y:+.2f}} · {nombre}<extra></extra>")
    fig.update_layout(barmode="overlay", bargap=0, yaxis_title=titulo_y, xaxis_hoverformat=E.FORMATO_MES,
                      yaxis=dict(range=[-3.5, 3.5], zeroline=True, zerolinewidth=1.5), hovermode="x",
                      xaxis=dict(range=[serie.index[0] - pd.DateOffset(months=1),
                                        serie.index[-1] + pd.DateOffset(months=1)]))
    grafica(fig, clave, 380)


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


def municipios_zona(id_zona: str) -> list[dict]:
    """Municipios de la zona con su contorno (INEGI), su centro y su caja, para resaltarlos y hacer zoom."""
    salida = []
    for f in region.contorno(id_zona)["features"]:
        if f["properties"]["tipo"] != "municipio":
            continue
        g = f["geometry"]
        anillo = max(([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]), key=lambda p: len(p[0]))[0]
        lons, lats = [p[0] for p in anillo], [p[1] for p in anillo]
        salida.append({"nombre": f["properties"]["nombre"], "rasgo": f, "lon": float(np.mean(lons)),
                       "lat": float(np.mean(lats)), "caja": (min(lons), min(lats), max(lons), max(lats))})
    return salida


def celda_del_centro(celdas_t: pd.DataFrame, lon: float, lat: float) -> pd.Series:
    """La celda de POWER más cercana al centro de un municipio."""
    return celdas_t.loc[((celdas_t["lon"] - lon) ** 2 + (celdas_t["lat"] - lat) ** 2).idxmin()]


def mapa_3d(celdas_t: pd.DataFrame, maximo: float, u_mapa: str, buscado: dict | None) -> pdk.Deck:
    """Mapa 3D con interacción completa y sin bloques: cada celda de POWER va plana, con relleno suave del color de
    su cambio y un borde que brilla (más fuerte si la tendencia es segura). El municipio buscado se resalta y la
    cámara hace zoom ahí."""
    dl, dt = region.PASO_LON / 2, region.PASO_LAT / 2
    celdas, bordes = [], []
    for _, c in celdas_t.iterrows():
        segura = c["color"] in SEGURAS
        v = E.VEREDICTO[c["color"]]
        color = E.rgb(E.color_cambio(c["pendiente"], maximo))
        cuadro = [[c["lon"] - dl, c["lat"] - dt], [c["lon"] + dl, c["lat"] - dt],
                  [c["lon"] + dl, c["lat"] + dt], [c["lon"] - dl, c["lat"] + dt]]
        celdas.append({"poligono": cuadro, "relleno": color + [175 if segura else 125],
                       "tip": (tx("donde.celda", lat=f"{c['lat']:.2f}", lon=f"{c['lon']:.3f}", peso=f"{c['peso']:.0%}")
                               + "\n" + tx("donde.por_decada", pend=f"{c['pendiente']:+.2f}", u=u_mapa,
                                           icono=v["icono"], palabra=E.palabra(c["color"], idioma))
                               + "\n" + re.sub(r"</?b>", "", tx("donde.segura" if segura else "donde.no_segura")))})
        camino = cuadro + [cuadro[0]]
        bordes.append({"camino": camino, "halo": (([255, 255, 255] if segura else color) + [95 if segura else 60]),
                       "ancho_halo": 14 if segura else 9, "linea": ([255, 255, 255, 255] if segura else color + [235]),
                       "ancho": 3.2 if segura else 1.6})
    contorno = region.contorno(id_zona)
    zona_geo = {"type": "FeatureCollection", "features": [f for f in contorno["features"]
                                                          if f["properties"]["tipo"] == "zona"]}
    munis = municipios_zona(id_zona)
    muni_geo = {"type": "FeatureCollection",  # cada municipio dice su nombre y que con un clic te acercas
                "features": [{**m["rasgo"], "properties": {**m["rasgo"]["properties"],
                                                           "tip": f"{m['nombre']}\n{tx('buscar.clic')}"}}
                             for m in munis]}
    estaciones = [{"lon": s["lon"], "lat": s["lat"],
                   "tip": tx("donde.estacion", nombre=s["nombre"], municipio=s["municipio"])}
                  for _, s in contraste.estaciones(id_zona).iterrows()]
    pixeles = {"width_units": pdk.types.String("pixels"), "cap_rounded": True, "joint_rounded": True}
    capas = [
        pdk.Layer("PolygonLayer", celdas, get_polygon="poligono", filled=True, stroked=False,
                  get_fill_color="relleno", pickable=True, auto_highlight=True, highlight_color=[255, 255, 255, 60]),
        pdk.Layer("PathLayer", bordes, get_path="camino", get_color="halo", get_width="ancho_halo", **pixeles),
        pdk.Layer("PathLayer", bordes, get_path="camino", get_color="linea", get_width="ancho", **pixeles),
        pdk.Layer("GeoJsonLayer", muni_geo, id="municipios", stroked=True, filled=True,
                  get_fill_color=[255, 255, 255, 0], get_line_color=[220, 235, 250, 120], line_width_min_pixels=1,
                  pickable=True, auto_highlight=True, highlight_color=[255, 212, 138, 70]),
        pdk.Layer("GeoJsonLayer", zona_geo, stroked=True, filled=False, get_line_color=E.rgb(E.BORDE_ZONA) + [70],
                  line_width_min_pixels=10),
        pdk.Layer("GeoJsonLayer", zona_geo, stroked=True, filled=False, get_line_color=E.rgb(E.BORDE_ZONA) + [255],
                  line_width_min_pixels=2.5),
    ]
    if buscado:  # el municipio buscado: relleno ámbar suave, halo ancho y borde blanco
        geo = {"type": "FeatureCollection", "features": [buscado["rasgo"]]}
        capas += [
            pdk.Layer("GeoJsonLayer", geo, stroked=True, filled=True, get_fill_color=E.rgb(E.BORDE_ZONA) + [70],
                      get_line_color=E.rgb(E.BORDE_ZONA) + [120], line_width_min_pixels=16),
            pdk.Layer("GeoJsonLayer", geo, stroked=True, filled=False, get_line_color=[255, 255, 255, 255],
                      line_width_min_pixels=3.5),
        ]
    capas += [
        pdk.Layer("ScatterplotLayer", estaciones, get_position=["lon", "lat"], get_radius=1500,
                  radius_min_pixels=3, get_fill_color=[255, 255, 255, 240], stroked=True,
                  get_line_color=E.rgb(E.CIELO_HONDO) + [255], line_width_min_pixels=1, pickable=True),
    ]
    if buscado:  # zoom al municipio: que su caja llene el mapa
        o, s_, e, n = buscado["caja"]
        zoom = float(np.clip(np.log2(360 / max(e - o, (n - s_) * 1.25)) - 0.55, 8.2, 10.8))
        vista = pdk.ViewState(latitude=(s_ + n) / 2 - 0.04, longitude=(o + e) / 2, zoom=zoom, pitch=48, bearing=-12,
                              transition_duration=1200)
    else:
        vista = pdk.ViewState(latitude=float(celdas_t["lat"].mean()) - 0.12, longitude=float(celdas_t["lon"].mean()),
                              zoom=7.2 if id_zona == "los-altos" else 7.75, pitch=45, bearing=-12,
                              transition_duration=1200)
    # Interacción completa: arrastrar, girar e inclinar (botón derecho o Ctrl), acercar con la rueda o doble clic
    return pdk.Deck(layers=capas, initial_view_state=vista, map_provider=None, map_style=None,
                    views=[pdk.View(type="MapView", controller=True)],
                    tooltip={"text": "{tip}", "style": {"backgroundColor": "rgba(6,26,51,0.94)", "color": E.NUBE,
                                                         "fontFamily": E.PILA_TEXTO, "fontSize": "13px",
                                                         "whiteSpace": "pre-line", "borderRadius": "12px",
                                                         "padding": "8px 10px"}})


# --- Controles: zona y periodo -------------------------------------------------------------
with st.container(key="controles"):
    c_zona, c_periodo = st.columns([1.15, 1], gap="large")
    with c_zona:
        id_zona = st.segmented_control(tx("panel.donde"), list(region.ZONAS), key="zona", default="los-altos",
                                       required=True, format_func=lambda z: region.obtener_zona(z, idioma)["nombre"])
        zona = region.obtener_zona(id_zona, idioma)
        st.caption(tx("panel.municipios", n=len(zona["municipios"]), lista=", ".join(zona["municipios"])))
    with c_periodo:
        a0, a1 = st.slider(tx("panel.periodo"), ANIO_MIN, ANIO_MAX, PERIODO_INICIAL, key="periodo")
        st.caption(tx("panel.normal"))

lugar = tx("lugar.los-altos") if id_zona == "los-altos" else zona["nombre"]
with cab:
    st.markdown(E.hero_html(tx("caso.numero", lugar=lugar, a0=a0, a1=a1), tx("caso.pregunta", lugar=lugar),
                            tx("caso.nota"), idioma), unsafe_allow_html=True)

if a1 - a0 + 1 < MIN_ANIOS:
    st.error(tx("error.periodo_corto", n=MIN_ANIOS))
    pie()
    st.stop()

try:
    with st.spinner(tx("spinner.descarga")):
        lluvia_toda, avisos_ll = cargar("precipitacion", id_zona)
        humedad_toda, avisos_hu = cargar(CAPA_INICIAL, id_zona)
except ValueError as e:
    st.error(tx("error.entrada", e=e))
    pie()
    st.stop()
except Exception as e:  # sin red y sin respaldo, servidor caído: aviso en vez de romper la app
    st.error(tx("error.descarga", e=type(e).__name__))
    pie()
    st.stop()

if any("Sin conexión" in a for a in avisos_ll + avisos_hu):
    st.warning(tx("aviso.sin_conexion"), icon=":material/inventory_2:")
    cargar.clear()  # la próxima vez se vuelve a intentar con NASA POWER
periodo = slice(f"{a0}-01-01", f"{a1}-12-01")
VAR_LLUVIA = catalogo.obtener_variable("precipitacion", idioma)

# --- Navegación: tres secciones; solo se dibuja la elegida (más rápido y bien medida en el celular) ----------
vista = st.segmented_control(tx("nav.etiqueta"), VISTAS, key="vista", default="resumen", required=True,
                             format_func=lambda v: f"{ICONO_VISTA[v]} {tx(f'tab.{v}')}",
                             label_visibility="collapsed", width="stretch")

# --- Panorama: el mapa 3D, y abajo lo que encontramos ----------------------------------------
if vista == "resumen":
    seccion("sec.donde")
    id_mapa = st.segmented_control(tx("donde.variable"), ("precipitacion", CAPA_INICIAL), key="var_mapa",
                                   default="precipitacion", required=True,
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
        munis = municipios_zona(id_zona)
        nombres_munis = [m["nombre"] for m in munis]
        # Clic en un municipio del mapa = buscarlo: se lee la selección del mapa anterior antes de dibujar el buscador.
        # Solo cuenta una selección nueva (si no, borrar el buscador volvería a poner el municipio del último clic).
        clave_previa = st.session_state.get("mapa3d_clave")
        seleccion = (st.session_state.get(clave_previa) or {}).get("selection") or {} if clave_previa else {}
        clic = (seleccion.get("objects") or {}).get("municipios") or []
        if clic and (clave_previa, str(seleccion.get("indices"))) != st.session_state.get("mapa3d_aplicado"):
            st.session_state["mapa3d_aplicado"] = (clave_previa, str(seleccion.get("indices")))
            nombre_clic = (clic[0].get("properties") or {}).get("nombre")
            if nombre_clic in nombres_munis:
                st.session_state["buscar"] = nombre_clic
        nombre_buscado = st.selectbox(tx("buscar.etiqueta"), nombres_munis, index=None, key="buscar",
                                      placeholder=tx("buscar.placeholder"))
        buscado = next((m for m in munis if m["nombre"] == nombre_buscado), None)
        # La llave cambia con la zona y el municipio buscado: así el mapa se vuelve a crear y la cámara hace zoom ahí
        clave_mapa = f"mapa3d_{id_zona}_{buscado['rasgo']['properties']['cvegeo'] if buscado else 'zona'}"
        st.session_state["mapa3d_clave"] = clave_mapa
        st.pydeck_chart(mapa_3d(celdas_t, maximo, u_mapa, buscado), height=560, key=clave_mapa,
                        on_select="rerun", selection_mode="single-object")
        if buscado:
            c = celda_del_centro(celdas_t, buscado["lon"], buscado["lat"])
            st.markdown(E.buscado_html(tx(
                "buscar.resultado", nombre=buscado["nombre"], pend=f"{c['pendiente']:+.2f}", u=u_mapa,
                icono=E.VEREDICTO[c["color"]]["icono"], palabra=E.palabra(c["color"], idioma),
                segura=tx("tabla.si") if c["color"] in SEGURAS else tx("tabla.no"))), unsafe_allow_html=True)
        seguras = int(celdas_t["color"].isin(SEGURAS).sum())
        st.markdown(E.leyenda_mapa_html(maximo, u_mapa, seguras, len(celdas_t), idioma), unsafe_allow_html=True)
        st.caption(tx("mapa.ayuda"))
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
    significa("donde")

    seccion("sec.resumen")
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
    significa("resumen")
    limites(tx("fuente_power"), tx("limites.resumen"), tx("limites.donde"))

# --- Lluvia y sequía -----------------------------------------------------------------------
elif vista == "lluvia":
    lluvia = lluvia_toda.loc[periodo]
    seccion("sec.lluvia")
    bloque_tendencia(lluvia, VAR_LLUVIA, a0, a1, "lluvia")

    acum = indices.acumulados(lluvia)
    normal = indices.acumulados(lluvia_toda.loc["1991-01-01":"2020-12-01"])["anual_mm"].mean()
    st.markdown(f"##### {tx('lluvia.acum.titulo')}")
    fig = go.Figure([
        go.Bar(x=acum.index, y=acum["anual_mm"], name=tx("lluvia.acum.anual"), marker_color=E.rgba(E.NIEBLA, 0.45),
               hovertemplate=tx("lluvia.acum.hover_anual") + "<extra></extra>"),
        go.Bar(x=acum.index, y=acum["temporada_mm"], name=tx("lluvia.acum.temporada"), marker_color=E.MAS_AGUA,
               hovertemplate=tx("lluvia.acum.hover_temp") + "<extra></extra>"),
    ])
    fig.add_hline(y=normal, line_dash="dash", line_color=E.NUBE, line_width=1.5,
                  annotation_text=tx("lluvia.acum.normal", mm=f"{normal:.0f}"), annotation_position="top left",
                  annotation_font=dict(family=E.PILA_NUMEROS, size=12, color=E.NUBE))
    fig.update_layout(barmode="group", yaxis_title="mm", bargap=0.25)
    grafica(fig, "acumulados", 340)
    incompletos = acum.index[~acum["completo"]].tolist()
    if incompletos:
        st.caption(tx("lluvia.acum.incompletos", lista=", ".join(map(str, incompletos))))
    significa("lluvia")

    seccion("sec.sequia")
    escala = st.segmented_control(tx("sequia.indice"), [3, 6], key="escala_spi", default=6, required=True,
                                  format_func=lambda e: tx("sequia.formato", e=e))
    try:
        spi_p = indices.spi(lluvia_toda, escala).loc[periodo]
        grafica_indice(spi_p.dropna(), "spi", f"SPI-{escala}", "spi")
        evidencias_indice(indices.resumen_indice(spi_p, "spi", idioma=idioma), "sequia", tx("palabra.sequia"))
    except ValueError as e:
        st.warning(tx("error.spi", e=e))
        spi_p = None
    significa("sequia")

    seccion("sec.comprobar")
    st.markdown(f"##### {tx('est.titulo')}")
    est_zona = contraste.estaciones(id_zona)
    comp_est = contraste.comparar_lluvia(lluvia, contraste.lluvia_estaciones(id_zona).loc[periodo])
    if comp_est is None:
        st.info(tx("est.sin"))
    else:
        anual = comp_est["anual"]
        fig = go.Figure([
            go.Scatter(x=anual.index, y=anual["estaciones"], name=tx("est.graf.est"), mode="lines+markers",
                       line=dict(color=E.NUBE, width=2, dash="dot"), hovertemplate="%{y:.0f} mm<extra></extra>"),
            go.Scatter(x=anual.index, y=anual["power"], name=tx("est.graf.power"), mode="lines+markers",
                       line=dict(color=E.MAS_AGUA, width=3), hovertemplate="%{y:.0f} mm<extra></extra>"),
        ])
        fig.update_layout(yaxis_title=tx("est.graf.eje"), hovermode="x unified")
        grafica(fig, "estaciones", 320)
        evidencias([
            (tx("est.n.titulo"), str(len(est_zona)), tx("est.n.nota"), ""),
            (tx("est.r.titulo"), f"{comp_est['r_anual']:.2f}", tx("est.r.nota", n=comp_est["anios"]),
             tx("est.r.ayuda")),
            (tx("est.dif.titulo"), f"{comp_est['diferencia_pct']:+.0f} %", tx("est.dif.nota"), ""),
        ], "estaciones")
    explica(tx("est.intro"))

    st.markdown(f"##### {tx('msm.titulo')}")
    msm = contraste.monitor(id_zona)
    msm_p = msm.loc[periodo]
    comp_msm = contraste.comparar_sequia(spi_p, msm_p["fraccion_sequia"]) if spi_p is not None else None
    if comp_msm is None:
        st.info(tx("msm.sin"))
    else:
        fig = go.Figure()
        for cat, color in E.MONITOR.items():
            fig.add_bar(x=msm_p.index, y=msm_p[cat], name=tx(f"msm.{cat}"), width=UN_MES,
                        marker=dict(color=color, line=dict(width=0)),
                        hovertemplate=f"%{{y}} · {tx(f'msm.{cat}')}<extra></extra>")
        fig.update_layout(barmode="stack", bargap=0, yaxis=dict(title=tx("msm.eje"), range=[0, int(msm["total"].iloc[0])]),
                          xaxis_hoverformat=E.FORMATO_MES, hovermode="x unified")
        grafica(fig, "monitor", 340)
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
    explica(tx("msm.intro"))
    limites(tx("fuente_power"), tx("limites.lluvia"), tx("limites.sequia"), tx("est.fuente", n=len(est_zona)),
            tx("est.limite"), tx("msm.fuente"), tx("msm.limite"))

# --- Agua del suelo ------------------------------------------------------------------------
else:
    capa = st.segmented_control(tx("humedad.capa"), CAPAS, key="capa", default=CAPA_INICIAL, required=True,
                                format_func=nombre_capa)
    try:
        humedad, _ = cargar(capa, id_zona)
        var_capa = catalogo.obtener_variable(capa, idioma)
    except Exception as e:
        st.error(tx("error.capa", e=type(e).__name__))
        pie()
        st.stop()
    seccion("sec.humedad")
    st.caption(var_capa["definicion"])
    bloque_tendencia(humedad.loc[periodo], var_capa, a0, a1, "humedad")
    significa("humedad")

    seccion("sec.estres")
    try:
        z = indices.estres_hidrico(humedad).loc[periodo]
        grafica_indice(z.dropna(), "estres", tx("estres.eje"), "estres")
        evidencias_indice(indices.resumen_indice(z, "estres", idioma=idioma), "estres", tx("palabra.deficit"))
    except Exception as e:
        st.warning(tx("error.estres", e=e))
    significa("estres")
    limites(tx("fuente_power"), tx("limites.humedad"), tx("limites.estres"))

# --- Fuentes -------------------------------------------------------------------------------
pie()
