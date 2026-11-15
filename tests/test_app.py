"""Pruebas de la app (fase Los Altos) con AppTest: 3 secciones, gráfica y luego "¿Qué significa?", sin internet."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src import datos, explicar

APP = str(Path(__file__).parent.parent / "app.py")
SECCIONES = ["resumen", "lluvia", "suelo"]
FECHAS = pd.date_range("1981-01-01", "2024-12-01", freq="MS")
SERIE_ZONA_REAL = datos.serie_zona
SERIE_PUNTO_REAL = datos.serie_punto


def serie_falsa(id_variable: str, semilla: int = 0) -> pd.Series:
    """Misma forma que el contrato: mensual 1981–2024, lluvia en mm/mes (con temporada) o humedad en %."""
    rng = np.random.default_rng(semilla)
    mes = FECHAS.month.to_numpy()
    if id_variable == "precipitacion":
        base = np.where((mes >= 6) & (mes <= 10), 140.0, 12.0)
        valores = base * rng.gamma(2.0, 0.5, len(FECHAS))
    else:
        valores = 45 + 12 * np.sin(2 * np.pi * (mes - 4) / 12) + rng.normal(0, 3, len(FECHAS))
        valores -= np.arange(len(FECHAS)) / 120 * 0.8  # se seca un poco por década
    return pd.Series(valores, index=FECHAS, name=id_variable)


@pytest.fixture(autouse=True)
def falsos(monkeypatch):
    st.cache_data.clear()
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(datos, "serie_zona",
                        lambda v, z, a0, a1: serie_falsa(v).loc[f"{a0}":f"{a1}"], raising=False)
    monkeypatch.setattr(datos, "serie_punto",
                        lambda v, lat, lon, a0, a1: serie_falsa(v, int(abs(lat * 10 + lon))).loc[f"{a0}":f"{a1}"],
                        raising=False)


def correr(idioma: str = "es", vista: str = "resumen") -> AppTest:
    """Corre la app (abre en inglés), cambia de idioma con el botón de abajo si se pide y abre una sección.

    Las pruebas que revisan textos en español usan "es"; las de la versión para los jueces, "en".
    """
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    if idioma != "en":
        at.segmented_control(key="idioma").set_value(idioma).run()
    if vista != "resumen":
        at.segmented_control(key="vista").set_value(vista).run()
    return at


def textos(elementos) -> str:
    return " ".join(e.value for e in elementos)


def opciones(at: AppTest, clave: str) -> list[str]:
    """Lo que dicen los botones de un control (AppTest ya los entrega con su texto)."""
    return list(at.segmented_control(key=clave).options)


def test_tres_secciones_y_nada_fuera_de_los_altos():
    at = correr()
    assert not at.exception
    assert [o.split(":")[-1].strip() for o in opciones(at, "vista")] == ["Panorama", "Lluvia y sequía", "Agua del suelo"]
    assert at.segmented_control(key="vista").value == "resumen"
    assert opciones(at, "zona") == ["Toda la región", "Altos Norte", "Altos Sur"]
    assert at.segmented_control(key="zona").value == "los-altos"
    assert at.slider(key="periodo").value == (2001, 2024)
    todo = textos(at.markdown) + textos(at.caption)
    assert "Comparar ciudades" not in todo and "Recuadro" not in todo
    assert "Caso Nº Los Altos · Lluvia y humedad del suelo · 2001–2024" in todo


@pytest.mark.parametrize("vista", SECCIONES)
def test_cada_seccion_muestra_primero_la_grafica_y_abajo_que_significa(vista):
    at = correr(vista=vista)
    assert not at.exception
    contenido = textos(at.markdown)
    assert "¿Qué significa?" in contenido and "Fuente y limitaciones" in contenido
    tipo = "deck_gl_json_chart" if vista == "resumen" else "plotly_chart"
    assert at.get(tipo)
    # recorre la página en orden: la primera gráfica o mapa llega antes del primer "¿Qué significa?"
    orden = []
    pendientes = list(at.main.children.values())
    while pendientes:
        e = pendientes.pop(0)
        if e.type == tipo:
            orden.append("grafica")
        elif e.type == "markdown" and "¿Qué significa?" in e.value:
            orden.append("significa")
        pendientes[:0] = list(getattr(e, "children", {}).values())
    assert orden[0] == "grafica"


def test_resumen_con_mapa_tarjetas_y_texto_de_plantillas():
    at = correr()
    resumen = textos(at.markdown)
    assert at.get("deck_gl_json_chart")
    assert "dd-tarjetas" in resumen and "Sequía meteorológica (SPI-6)" in resumen
    assert "Resumen en palabras sencillas" in resumen
    assert "Escrito con plantillas" in resumen  # sin clave de Gemini


def test_resumen_de_gemini_se_escapa(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    falso = {"titular": "<script>alert(1)</script>Llueve igual", "resumen": "Todo normal.", "puntos": [],
             "cuidado": ["Cada dato cubre unos 50 km."], "para_pensar": ""}
    monkeypatch.setattr(explicar, "resumen_con_gemini", lambda r, clave=None, modelo=None, **k: falso)
    at = correr()
    resumen = textos(at.markdown)
    assert "Escrito por Gemini" in resumen
    assert "<script>" not in resumen and "&lt;script&gt;" in resumen


def test_lluvia_veredicto_evidencias_descarga_y_comprobaciones():
    at = correr(vista="lluvia")
    contenido = textos(at.markdown)
    assert "dd-sello" in contenido and "Qué no es" in contenido
    etiquetas = [m.label for m in at.metric]
    assert etiquetas[0] == "Evidencia 01 · Cambio por década" and "mm/mes" in at.metric[0].value
    assert "Evidencia 01 · Meses en sequía" in etiquetas
    assert at.get("download_button")
    assert "Comprobación en tierra" in contenido and "Monitor de Sequía" in contenido


def test_sequia_spi_3_y_6():
    at = correr(vista="lluvia")
    at.segmented_control(key="escala_spi").set_value(3).run()
    assert not at.exception
    meses = [m for m in at.metric if m.label == "Evidencia 01 · Meses en sequía"]
    assert meses and " / " in meses[0].value


def test_suelo_con_las_tres_capas():
    at = correr(vista="suelo")
    capa = at.segmented_control(key="capa")
    assert capa.value == "humedad_raices" and len(capa.options) == 3
    for opcion in ("humedad_superficie", "humedad_perfil"):
        at.segmented_control(key="capa").set_value(opcion).run()
        assert not at.exception
        assert "% de saturación" in at.metric[0].value


def test_estres_aclara_que_no_mide_el_estres_de_los_cultivos():
    at = correr(vista="suelo")
    assert "No mide directamente el estrés de los cultivos" in textos(at.markdown)
    assert "Evidencia 01 · Meses en déficit" in [m.label for m in at.metric]


def test_mapa_con_leyenda_y_tabla():
    at = correr()
    contenido = textos(at.markdown)
    assert "menos agua" in contenido and "más agua" in contenido
    assert "55 × 65 km" in contenido + textos(at.caption)
    assert at.dataframe
    at.segmented_control(key="var_mapa").set_value("humedad_raices").run()
    assert not at.exception


def test_cambiar_de_zona():
    at = correr()
    at.segmented_control(key="zona").set_value("altos-norte").run()
    assert not at.exception
    assert "Caso Nº Altos Norte" in textos(at.markdown)
    assert "Villa Hidalgo" in textos(at.caption)


def test_periodo_corto_avisa_sin_romper_ni_perder_el_idioma():
    at = correr()
    at.slider(key="periodo").set_value((2016, 2020)).run()
    assert not at.exception
    assert "al menos 10 años" in at.error[0].value
    assert at.segmented_control(key="idioma").value == "es"


def test_abre_con_los_datos_guardados_sin_descargar_nada(monkeypatch, tmp_path):
    """Visitante nuevo (sin caché) y sin red: todo sale de demos/ al instante, sin avisos ni descargas."""
    monkeypatch.setattr(datos, "serie_zona", SERIE_ZONA_REAL)
    monkeypatch.setattr(datos, "serie_punto", SERIE_PUNTO_REAL)
    monkeypatch.setattr(datos, "CARPETA_DATOS", tmp_path)
    llamadas = []

    def caido(params):
        llamadas.append(params)
        raise ConnectionError("No se pudo descargar de NASA POWER: sin red (simulado)")

    monkeypatch.setattr(datos, "_pedir_json", caido)
    at = correr()
    assert not at.exception and not at.error
    assert "menos agua" in textos(at.markdown)
    at.segmented_control(key="vista").set_value("lluvia").run()
    assert not at.exception and not at.error
    assert llamadas == []  # ni una descarga
    assert not any("Sin conexión" in w.value for w in at.warning)
    assert "dd-sello" in textos(at.markdown)


def test_sin_internet_ni_respaldo_avisa_sin_romper(monkeypatch):
    def falla(*_a, **_k):
        raise ConnectionError("sin red")

    monkeypatch.setattr(datos, "serie_zona", falla)
    at = correr()
    assert not at.exception
    assert "No se pudieron descargar" in at.error[0].value


def test_css_sin_etiquetas_html_dentro():
    """st.html descarta el bloque de estilos completo si la CSS trae algo como una etiqueta HTML."""
    from src import estilo
    assert estilo.CSS.startswith("<style>") and estilo.CSS.endswith("</style>")
    assert estilo.CSS.count("<") == 2 and estilo.CSS.count(">") == 2


def test_fondo_3d_trae_el_relieve():
    from src import fondo
    pagina = fondo.html()
    assert "three@0.160.0" in pagina and '"alturas":[[' in pagina and "prefers-reduced-motion" in pagina


def test_mapa_distingue_las_celdas_con_tendencia_segura():
    at = correr()
    contenido = textos(at.markdown)
    assert "tendencia segura" in contenido and "celdas con tendencia segura" in contenido
    tabla = at.dataframe[0].value
    assert "¿Tendencia segura?" in tabla.columns
    assert set(tabla["¿Tendencia segura?"]) <= {"Sí", "Todavía no"}


@pytest.mark.parametrize("vista, palabra", [("lluvia", "sequía"), ("suelo", "déficit")])
def test_ultimos_5_anios_se_lee_bien(vista, palabra):
    at = correr(vista=vista)
    evidencia = next(m for m in at.metric if m.label == "Evidencia 02 · Últimos 5 años")
    assert evidencia.value.endswith(f"meses en {palabra}")
    assert "Desde enero de 2020 hasta diciembre de 2024." in textos(at.caption)


# --- Inglés (lo que ven los jueces) ---------------------------------------------------------
RASTROS_ES = ["¿Qué significa?", "Evidencia ", "Fuente y limitaciones", "Veredicto", "Fuentes del expediente",
              "Panel del detective", " por década", "Resumen en palabras", "Toda la región", "Caso Nº",
              "Sequía", "Lluvia", "Humedad del suelo", "Escrito con plantillas", "Panorama", "Agua del suelo"]


def test_abre_en_ingles():
    at = correr("en")
    assert not at.exception and not at.error
    assert at.segmented_control(key="idioma").value == "en"
    assert [o.split(":")[-1].strip() for o in opciones(at, "vista")] == ["Overview", "Rain and drought", "Soil water"]
    assert opciones(at, "zona") == ["Whole region", "Altos Norte", "Altos Sur"]
    todo = textos(at.markdown)
    assert "Case No. Los Altos · Rainfall and soil moisture · 2001–2024" in todo
    assert "What is happening to the water in Los Altos?" in todo
    assert "What does it mean?" in todo and "Case file sources" in todo
    at.segmented_control(key="vista").set_value("lluvia").run()
    assert "Verdict:" in textos(at.markdown)
    assert at.metric[0].label == "Evidence 01 · Change per decade" and "mm/month" in at.metric[0].value


@pytest.mark.parametrize("vista", SECCIONES)
def test_en_ingles_no_quedan_textos_en_espanol(vista):
    at = correr("en", vista)
    texto = (textos(at.markdown) + textos(at.caption) + " ".join(m.label + " " + m.value for m in at.metric)
             + " ".join(opciones(at, "zona") + opciones(at, "vista")))
    # los nombres de los municipios y de las fuentes de CONAGUA se quedan como son
    for nombre in ("Encarnación de Díaz", "Cañadas de Obregón"):
        texto = texto.replace(nombre, "")
    assert [r for r in RASTROS_ES if r in texto] == []


def test_en_ingles_indices_resumen_y_mapa():
    at = correr("en", "lluvia")
    meses = next(m for m in at.metric if m.label == "Evidence 01 · Months in drought")
    assert " / " in meses.value
    assert "From January 2020 to December 2024." in textos(at.caption)
    at = correr("en", "suelo")
    assert "No crop" not in textos(at.markdown)
    assert "It does not directly measure crop stress" in textos(at.markdown)
    at = correr("en")
    resumen = textos(at.markdown)
    assert "Summary in plain words" in resumen and "Written with templates" in resumen
    assert "significant trend" in resumen
    assert "Significant trend?" in at.dataframe[0].value.columns


def test_el_boton_cambia_todo_y_regresa():
    at = correr("en")
    at.segmented_control(key="idioma").set_value("es").run()
    assert "Caso Nº" in textos(at.markdown) and "¿Qué significa?" in textos(at.markdown)
    at.segmented_control(key="idioma").set_value("en").run()
    assert not at.exception
    assert "Case No." in textos(at.markdown)


def test_buscar_un_municipio_hace_zoom_y_lo_resalta_sin_bloques():
    import json
    at = correr()
    mapa = json.loads(at.get("deck_gl_json_chart")[0].proto.json)
    assert not any(c.get("extruded") for c in mapa["layers"])  # nada de bloques
    at.selectbox(key="buscar").set_value("Tepatitlán de Morelos").run()
    assert not at.exception
    assert "Tepatitlán de Morelos: la celda de NASA POWER sobre su centro" in textos(at.markdown)
    mapa = json.loads(at.get("deck_gl_json_chart")[0].proto.json)
    assert mapa["initialViewState"]["zoom"] > 8
