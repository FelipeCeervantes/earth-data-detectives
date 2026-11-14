"""Pruebas de los textos de la interfaz en inglés y español."""

import pytest

from src import catalogo, region
from src import textos as T


def test_los_dos_idiomas_tienen_las_mismas_claves():
    assert set(T.TEXTOS["en"]) == set(T.TEXTOS["es"])


def test_t_pone_los_campos_y_rechaza_idiomas_raros():
    assert T.t("caso.pregunta", "en", lugar="Los Altos") == "What is happening to the water in Los Altos?"
    assert T.t("caso.pregunta", "es", lugar="Los Altos") == "¿Qué está pasando con el agua en Los Altos?"
    with pytest.raises(ValueError):
        T.t("tab.lluvia", "fr")


def test_meses():
    assert T.mes_largo(1, 2020, "en") == "January 2020"
    assert T.mes_largo(1, 2020, "es") == "enero de 2020"
    assert T.mes_corto(8, "en") == "Aug" and T.mes_corto(8, "es") == "ago"


def test_catalogo_en_los_dos_idiomas():
    for v in catalogo.VARIABLES:
        en, es = catalogo.obtener_variable(v, "en"), catalogo.obtener_variable(v, "es")
        assert en["nombre"] != es["nombre"] and en["definicion"] != es["definicion"]
        assert en["parametro_power"] == es["parametro_power"] and en["tipo"] == es["tipo"]
    assert catalogo.obtener_variable("precipitacion", "en")["unidades"] == "mm/month"
    assert catalogo.obtener_variable("precipitacion")["unidades"] == "mm/mes"  # el español sigue por defecto
    assert [v["nombre"] for v in catalogo.listar_variables("en")][0] == "Rainfall"
    with pytest.raises(ValueError):
        catalogo.obtener_variable("precipitacion", "fr")


def test_zonas_en_los_dos_idiomas():
    assert region.obtener_zona("los-altos", "en")["nombre"] == "Whole region"
    assert region.obtener_zona("los-altos", "es")["nombre"] == "Toda la región"
    assert region.obtener_zona("altos-sur", "en")["municipios"] == region.ZONAS["altos-sur"]["municipios"]
