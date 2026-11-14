"""Fase Los Altos: resultados para la IA, resumen con plantillas y Gemini con respaldo (sin red)."""

import json

import numpy as np
import pandas as pd
import pytest
import requests

from src import explicar

IDX = pd.date_range("1981-01-01", "2024-12-01", freq="MS")
MEDIA_MES = np.array([12, 5, 3, 5, 20, 140, 190, 170, 130, 50, 12, 8], dtype=float)


def lluvia(seca_desde: int | None = None) -> pd.Series:
    rng = np.random.default_rng(0)
    v = rng.gamma(2.0, MEDIA_MES[IDX.month - 1] / 2.0)
    if seca_desde:
        v[IDX.year >= seca_desde] *= 0.6
    return pd.Series(v, index=IDX, name="precipitacion")


def humedad(baja: float = 0.0) -> pd.Series:
    rng = np.random.default_rng(1)
    t = (IDX.year - 1981) + (IDX.month - 1) / 12
    v = 40 + 15 * np.sin(2 * np.pi * (IDX.month - 4) / 12) - baja * t / 10 + rng.normal(0, 2, len(IDX))
    return pd.Series(v, index=IDX, name="humedad_raices")


@pytest.fixture
def res():
    return explicar.resultados("Toda la región", (2001, 2024), lluvia(), humedad())


def test_resultados_tiene_la_forma_de_la_tarea_09(res):
    for clave in ("region", "zona", "periodo", "referencia_normal", "fuente", "lluvia", "sequia_meteorologica",
                  "humedad_suelo", "estres_hidrico_suelo", "limitaciones"):
        assert clave in res
    assert res["periodo"] == "2001-2024" and res["referencia_normal"] == "1991-2020"
    assert 500 < res["lluvia"]["promedio_anual_mm"] < 900
    assert res["lluvia"]["tendencia"]["veredicto"] in ("sube", "baja", "no concluyente", "sin tendencia")
    assert res["sequia_meteorologica"]["meses_totales"] == 288
    assert "p_mann_kendall_estacional" in res["humedad_suelo"]["tendencia"]
    json.dumps(res)                                     # se puede mandar tal cual


def test_resultados_detecta_baja_de_humedad():
    r = explicar.resultados("Altos Sur", (2001, 2024), lluvia(), humedad(baja=4.0))
    assert r["humedad_suelo"]["tendencia"]["veredicto"] == "baja"
    s = explicar.resumen_sin_ia(r)                       # inglés por defecto
    assert "going down" in s["titular"] and "Altos Sur" in s["titular"]
    es = explicar.resumen_sin_ia(r, idioma="es")
    assert "baja" in es["titular"] and "Altos Sur" in es["titular"]


def test_pista_por_temporada_y_zona_en_minusculas():
    r = explicar.resultados("Toda la región", (2001, 2024), lluvia(), humedad(), idioma="es")
    r["humedad_suelo"]["tendencia"].update(veredicto="sin tendencia", tendencia_estacional="baja")
    s = explicar.resumen_sin_ia(r)
    assert "toda la región" in s["titular"]
    humedad_txt = next(p["texto"] for p in s["puntos"] if p["tema"] == "humedad")
    assert "prueba por temporada" in humedad_txt and "sí baja" in humedad_txt


def test_sin_humedad_y_periodo_corto():
    r = explicar.resultados("Altos Norte", (2023, 2024), lluvia(), None, idioma="es")
    assert r["humedad_suelo"] is None and r["estres_hidrico_suelo"] is None
    assert r["lluvia"]["tendencia"] is None             # 2 años: muy poco para hablar de tendencia
    s = explicar.resumen_sin_ia(r)
    assert any("No hay datos suficientes" in p["texto"] for p in s["puntos"])


def test_resumen_sin_ia_no_inventa_cifras(res):
    s = explicar.resumen_sin_ia(res)
    assert set(s) >= {"titular", "resumen", "puntos", "cuidado", "para_pensar"}
    assert explicar._es_valida(s)
    assert explicar.cifras_inventadas(s, res) == set()


def test_gemini_sin_clave_regresa_none(res, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert explicar.resumen_con_gemini(res) is None


class Respuesta:
    def __init__(self, salida, status_code=200):
        self.salida, self.status_code = salida, status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(self.salida)}]}}]}


def test_gemini_valido_y_cifras_inventadas(res, monkeypatch):
    buena = explicar.resumen_sin_ia(res)
    enviado = {}

    def falso_post(url, json, timeout, headers):
        enviado.update(url=url, headers=headers, cuerpo=json)
        return Respuesta(buena)

    monkeypatch.setattr(explicar.requests, "post", falso_post)
    assert explicar.resumen_con_gemini(res, clave="clave-de-prueba", idioma="es") == buena
    assert "clave-de-prueba" not in enviado["url"]        # la clave va en el encabezado
    assert "gemini-4-hydrogen" in enviado["url"]
    assert enviado["cuerpo"]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "LOW"}
    assert "IDIOMA" not in enviado["cuerpo"]["system_instruction"]["parts"][0]["text"]

    explicar.resumen_con_gemini(res, clave="x", pregunta="¿Es culpa del agave?")   # inglés por defecto
    assert "IMPORTANTE DE IDIOMA" in enviado["cuerpo"]["system_instruction"]["parts"][0]["text"]
    assert "Consulta del usuario: ¿Es culpa del agave?" in enviado["cuerpo"]["contents"][0]["parts"][0]["text"]

    mala = dict(buena, resumen=buena["resumen"] + " La lluvia bajó 37.5 % por el agave.")
    monkeypatch.setattr(explicar.requests, "post", lambda *a, **k: Respuesta(mala))
    assert explicar.resumen_con_gemini(res, clave="x") is None   # 37.5 no viene en los resultados
    assert "37.5" in explicar.ULTIMO_ERROR


def test_gemini_reintenta_sin_thinking_si_el_modelo_no_lo_acepta(res, monkeypatch):
    buena, llamadas = explicar.resumen_sin_ia(res), []

    def post(url, json, timeout, headers):
        llamadas.append("thinkingConfig" in json["generationConfig"])
        return Respuesta(buena, 400 if llamadas[-1] else 200)

    monkeypatch.setattr(explicar.requests, "post", post)
    assert explicar.resumen_con_gemini(res, clave="x") == buena
    assert llamadas == [True, False]


def test_gemini_falla_la_red(res, monkeypatch):
    def caido(*a, **k):
        raise requests.ConnectionError("sin red")
    monkeypatch.setattr(explicar.requests, "post", caido)
    assert explicar.resumen_con_gemini(res, clave="x") is None


def test_resultados_y_resumen_en_ingles_por_defecto(res):
    assert res["idioma"] == "en" and "municipalities" in res["region"]
    assert res["limitaciones"][0].startswith("Each data point")
    assert res["sequia_meteorologica"]["categoria_peor"] in ("Extreme drought", "Severe drought", "Moderate drought")
    s = explicar.resumen_sin_ia(res)
    assert s["resumen"].startswith("From 2001 to 2024") and "the whole" not in s["titular"]
    assert explicar.cifras_inventadas(s, res) == set()
    r_es = explicar.resultados("Toda la región", (2001, 2024), lluvia(), humedad(), idioma="es")
    s_es = explicar.resumen_sin_ia(r_es)                 # toma el idioma de los resultados
    assert s_es["resumen"].startswith("Entre 2001 y 2024") and "toda la región" in s_es["titular"]
    assert explicar.cifras_inventadas(s_es, r_es) == set()
    with pytest.raises(ValueError):
        explicar.resultados("x", (2001, 2024), lluvia(), None, idioma="fr")
