"""Fase Los Altos: acumulados, SPI y estrés hídrico del suelo con datos sintéticos de resultado conocido."""

import numpy as np
import pandas as pd
import pytest

from src.indices import acumulados, categoria, estres_hidrico, resumen_indice, spi

IDX = pd.date_range("1981-01-01", "2024-12-01", freq="MS")
# Lluvia parecida a Los Altos: casi todo cae de junio a octubre y en marzo a veces no llueve nada.
MEDIA_MES = np.array([12, 5, 3, 5, 20, 140, 190, 170, 130, 50, 12, 8], dtype=float)


def lluvia(semilla: int = 0) -> pd.Series:
    rng = np.random.default_rng(semilla)
    medias = MEDIA_MES[IDX.month - 1]
    valores = rng.gamma(shape=2.0, scale=medias / 2.0)
    valores[(IDX.month == 3) & (rng.random(len(IDX)) < 0.3)] = 0.0   # meses secos de verdad
    return pd.Series(valores, index=IDX, name="precipitacion")


def humedad(semilla: int = 0) -> pd.Series:
    rng = np.random.default_rng(semilla)
    estacional = 40 + 15 * np.sin(2 * np.pi * (IDX.month - 4) / 12)
    return pd.Series(estacional + rng.normal(0, 3, len(IDX)), index=IDX, name="humedad_raices")


def en_ref(s: pd.Series) -> pd.Series:
    return s[(s.index.year >= 1991) & (s.index.year <= 2020)].dropna()


def test_acumulados_y_faltantes():
    s = pd.Series(10.0, index=pd.date_range("2001-01-01", "2003-12-01", freq="MS"))
    s.iloc[1] = np.nan                     # febrero de 2001: fuera de temporada
    s.loc["2002-07-01"] = np.nan           # julio de 2002: dentro de la temporada
    a = acumulados(s)
    assert a.loc[2003, "anual_mm"] == 120 and a.loc[2003, "temporada_mm"] == 50 and a.loc[2003, "completo"]
    assert np.isnan(a.loc[2001, "anual_mm"]) and a.loc[2001, "temporada_mm"] == 50 and not a.loc[2001, "completo"]
    assert np.isnan(a.loc[2002, "temporada_mm"])   # nunca cuenta un faltante como 0


def test_acumulados_anio_parcial():
    s = pd.Series(10.0, index=pd.date_range("2001-03-01", "2001-12-01", freq="MS"))
    assert np.isnan(acumulados(s).loc[2001, "anual_mm"])   # faltan enero y febrero


@pytest.mark.parametrize("escala", [3, 6])
def test_spi_es_normal_en_la_referencia(escala):
    v = en_ref(spi(lluvia(), escala=escala))
    assert abs(v.mean()) < 0.1
    assert v.std() == pytest.approx(1.0, abs=0.12)
    assert np.isfinite(v).all()


def test_spi_detecta_una_sequia_y_maneja_ceros():
    s = lluvia(1)
    s.loc["2012-01-01":"2012-12-01"] *= 0.2         # un año con 80 % menos lluvia
    r = spi(s, escala=6)
    assert r.loc["2012-10-01"] <= -1.5
    assert np.isfinite(r.dropna()).all()            # los meses sin lluvia no dan infinitos


def test_spi_mes_faltante_corta_la_ventana():
    s = lluvia(2)
    s.loc["2010-05-01"] = np.nan
    r = spi(s, escala=3)
    assert r.loc["2010-05-01":"2010-07-01"].isna().all()
    assert r.loc["2010-08-01"] == r.loc["2010-08-01"]   # vuelve a haber valor


def test_referencia_muy_corta():
    corta = lluvia().loc["2015-01-01":]
    with pytest.raises(ValueError, match="referencia"):
        spi(corta)


def test_estres_hidrico():
    s = humedad(3)
    z = estres_hidrico(s)
    v = en_ref(z)
    assert abs(v.mean()) < 0.05 and v.std() == pytest.approx(1.0, abs=0.05)
    s.loc["2021-01-01":"2021-06-01"] -= 9            # suelo 3 desviaciones más seco
    seco = estres_hidrico(s).loc["2021-01-01":"2021-06-01"]
    assert (seco <= -1).all() and seco.mean() < -2.5


@pytest.mark.parametrize("valor, nivel, deficit", [
    (-2.3, "extremo", True), (-1.7, "severo", True), (-1.0, "moderado", True),
    (-0.5, "normal", False), (1.2, "humedo", False), (np.nan, "sin-dato", False),
])
def test_categoria(valor, nivel, deficit):
    c = categoria(valor, "spi")
    assert c["nivel"] == nivel and c["en_deficit"] == deficit
    assert categoria(-1.7, "estres", idioma="es")["nombre"] == "Déficit severo"
    assert categoria(-1.7, "estres")["nombre"] == "Severe deficit"   # inglés por defecto


def test_resumen_indice():
    idx = pd.date_range("2015-01-01", "2024-12-01", freq="MS")
    s = pd.Series(0.0, index=idx)
    s.loc["2016-03-01":"2016-04-01"] = -1.2          # racha corta
    s.loc["2020-09-01":"2021-01-01"] = -1.6          # la peor (5 meses)
    s.loc["2020-12-01"] = -2.2
    s.iloc[-1] = -1.1
    r = resumen_indice(s, "spi", ultimos_anios=5, idioma="es")
    assert r["peor_periodo"] == ("2020-09", "2021-01")
    assert r["categoria_peor"] == "Sequía extrema"
    assert r["meses_en_deficit"] == 8 and r["meses_totales"] == 120
    assert r["meses_en_deficit_ultimos"] == 6         # 2020-09 a 2021-01 y el último mes
    assert r["ultimo_mes"] == "2024-12" and r["categoria_ultimo"] == "Sequía moderada"
    en = resumen_indice(s, "spi", ultimos_anios=5)
    assert en["categoria_peor"] == "Extreme drought" and en["categoria_ultimo"] == "Moderate drought"
