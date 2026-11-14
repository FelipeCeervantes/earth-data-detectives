"""Pruebas de la app (fase Los Altos) con AppTest: 6 pestañas, "¿Qué significa?", sin internet y accesibilidad."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src import datos, explicar

APP = str(Path(__file__).parent.parent / "app.py")
PESTANAS = ["Resumen", "Lluvia", "Sequía meteorológica", "Humedad del suelo", "Estrés hídrico del suelo", "¿Dónde?"]
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


def correr() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    return at


def textos(elementos) -> str:
    return " ".join(e.value for e in elementos)


def test_seis_pestanas_y_nada_fuera_de_los_altos():
    at = correr()
    assert not at.exception
    assert [t.label for t in at.tabs] == PESTANAS
    zona = at.selectbox(key="zona")
    assert zona.options == ["Toda la región", "Altos Norte", "Altos Sur"]
    assert at.slider(key="periodo").value == (2001, 2024)
    todo = textos(at.markdown) + textos(at.caption)
    assert "Comparar ciudades" not in todo and "Recuadro" not in todo
    assert "Caso Nº Los Altos · Lluvia y humedad del suelo · 2001–2024" in todo


def test_cada_pestana_explica_que_significa_y_sus_limites():
    at = correr()
    for pestana in at.tabs:
        contenido = textos(pestana.markdown)
        assert "¿Qué significa?" in contenido, pestana.label
        assert "Fuente y limitaciones" in contenido, pestana.label


def test_resumen_con_tarjetas_y_texto_de_plantillas():
    at = correr()
    resumen = textos(at.tabs[0].markdown)
    assert "dd-tarjetas" in resumen and "Sequía meteorológica (SPI-6)" in resumen
    assert "Resumen en palabras sencillas" in resumen
    assert "Escrito con plantillas" in resumen  # sin clave de Gemini


def test_resumen_de_gemini_se_escapa(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    falso = {"titular": "<script>alert(1)</script>Llueve igual", "resumen": "Todo normal.", "puntos": [],
             "cuidado": ["Cada dato cubre unos 50 km."], "para_pensar": ""}
    monkeypatch.setattr(explicar, "resumen_con_gemini", lambda r, clave=None, modelo=None, **k: falso)
    at = correr()
    resumen = textos(at.tabs[0].markdown)
    assert "Escrito por Gemini" in resumen
    assert "<script>" not in resumen and "&lt;script&gt;" in resumen


def test_lluvia_veredicto_evidencias_y_descarga():
    at = correr()
    lluvia = at.tabs[1]
    assert "dd-sello" in textos(lluvia.markdown)
    etiquetas = [m.label for m in lluvia.metric]
    assert etiquetas[0] == "Evidencia 01 · Cambio por década" and "mm/mes" in lluvia.metric[0].value
    assert lluvia.get("download_button")


def test_sequia_spi_3_y_6():
    at = correr()
    sequia = at.tabs[2]
    assert [m.label for m in sequia.metric][0] == "Evidencia 01 · Meses en sequía"
    assert "Qué no es" in textos(sequia.markdown)
    at.radio(key="escala_spi").set_value(3).run()
    assert not at.exception
    assert " de " in at.tabs[2].metric[0].value


def test_humedad_con_las_tres_capas():
    at = correr()
    capa = at.radio(key="capa")
    assert capa.value == "humedad_raices" and len(capa.options) == 3
    for opcion in ("humedad_superficie", "humedad_perfil"):
        at.radio(key="capa").set_value(opcion).run()
        assert not at.exception
        assert "% de saturación" in at.tabs[3].metric[0].value


def test_estres_aclara_que_no_mide_el_estres_de_los_cultivos():
    at = correr()
    estres = at.tabs[4]
    assert "No mide directamente el estrés de los cultivos" in textos(estres.markdown)
    assert [m.label for m in estres.metric][0] == "Evidencia 01 · Meses en déficit"


def test_donde_mapa_con_leyenda_y_tabla():
    at = correr()
    donde = at.tabs[5]
    contenido = textos(donde.markdown)
    assert "menos agua" in contenido and "más agua" in contenido
    assert "50 km" in contenido or "55 × 65 km" in contenido
    assert donde.get("iframe") or donde.get("arrow_data_frame") or donde.dataframe
    at.radio(key="var_mapa").set_value("precipitacion").run()
    assert not at.exception


def test_cambiar_de_zona():
    at = correr()
    at.selectbox(key="zona").set_value("altos-norte").run()
    assert not at.exception
    assert "Caso Nº Altos Norte" in textos(at.markdown)
    assert "Villa Hidalgo" in textos(at.sidebar.caption)


def test_periodo_corto_avisa_sin_romper():
    at = correr()
    at.slider(key="periodo").set_value((2016, 2020)).run()
    assert not at.exception
    assert "al menos 10 años" in at.error[0].value


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
    assert llamadas == []  # ni una descarga
    assert not any("Sin conexión" in w.value for w in at.warning)
    assert "dd-sello" in textos(at.tabs[1].markdown)
    assert "menos agua" in textos(at.tabs[5].markdown)


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


def test_mapa_distingue_las_celdas_con_tendencia_segura():
    at = correr()
    donde = at.tabs[5]
    contenido = textos(donde.markdown)
    assert "Borde grueso: tendencia segura" in contenido and "celdas con tendencia segura" in contenido
    tabla = donde.dataframe[0].value
    assert "¿Tendencia segura?" in tabla.columns
    assert set(tabla["¿Tendencia segura?"]) <= {"Sí", "Todavía no"}


def test_ultimos_5_anios_se_lee_bien():
    at = correr()
    for pestana, palabra in ((at.tabs[2], "sequía"), (at.tabs[4], "déficit")):
        evidencia = pestana.metric[1]
        assert evidencia.label == "Evidencia 02 · Últimos 5 años"
        assert evidencia.value.endswith(f"meses en {palabra}")
        assert "Desde enero de 2020 hasta diciembre de 2024." in textos(pestana.caption)
