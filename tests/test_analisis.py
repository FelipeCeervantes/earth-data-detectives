"""Fase 1: el análisis recupera tendencias sintéticas conocidas."""

import numpy as np
import pandas as pd
import pytest

from src.analisis import anomalias, mann_kendall, tendencia_ols, veredicto


def sintetica(por_decada: float, anios: int = 40, ruido: float = 0.3, semilla: int = 0) -> pd.Series:
    """Serie mensual con ciclo estacional, tendencia lineal conocida y ruido."""
    idx = pd.date_range("1984-01-01", periods=anios * 12, freq="MS")
    t = np.arange(len(idx)) / 120  # décadas
    estacional = 8 * np.sin(2 * np.pi * (idx.month - 1) / 12)
    ruido_ = np.random.default_rng(semilla).normal(0, ruido, len(idx))
    return pd.Series(15 + estacional + por_decada * t + ruido_, index=idx, name="temperatura")


def test_anomalias_media_cero_por_mes():
    a = anomalias(sintetica(0.3))
    assert np.allclose(a.groupby(a.index.month).mean(), 0, atol=1e-9)


def test_ols_recupera_tendencia():
    r = tendencia_ols(anomalias(sintetica(0.3)))
    assert r["pendiente_decada"] == pytest.approx(0.3, abs=0.05)
    assert r["ic_bajo"] < 0.3 < r["ic_alto"]
    assert r["p_valor"] < 0.05
    assert r["n"] == 480


def test_mann_kendall_detecta_tendencia_y_sen():
    r = mann_kendall(anomalias(sintetica(-0.3)))
    assert r["tendencia"] == "bajada"
    assert r["p_valor"] < 0.05
    assert r["pendiente_sen_decada"] == pytest.approx(-0.3, abs=0.05)


def test_tolera_meses_faltantes():
    s = sintetica(0.3)
    s.iloc[::7] = np.nan
    r = tendencia_ols(anomalias(s))
    assert r["pendiente_decada"] == pytest.approx(0.3, abs=0.05)
    assert mann_kendall(anomalias(s))["pendiente_sen_decada"] == pytest.approx(0.3, abs=0.05)


def test_sin_tendencia_en_ruido():
    s = anomalias(sintetica(0.0, semilla=1))
    assert veredicto(tendencia_ols(s), mann_kendall(s), "°C")["color"] == "gris"


def test_pocos_datos_da_error():
    with pytest.raises(ValueError):
        tendencia_ols(sintetica(0.3, anios=1))


@pytest.mark.parametrize("ols_p, mk_p, pendiente, color", [
    (0.001, 0.001, 0.3, "rojo"),       # subida
    (0.001, 0.001, -0.3, "verde"),     # bajada
    (0.001, 0.20, 0.3, "amarillo"),    # no significativa (solo una prueba)
    (0.40, 0.50, 0.01, "gris"),        # sin tendencia
])
def test_veredicto(ols_p, mk_p, pendiente, color):
    ols = {"pendiente_decada": pendiente, "ic_bajo": pendiente - 0.1, "ic_alto": pendiente + 0.1, "p_valor": ols_p, "n": 480}
    mk = {"tendencia": "x", "p_valor": mk_p, "pendiente_sen_decada": pendiente}
    v = veredicto(ols, mk, "°C")
    assert v["color"] == color and v["texto"]


# --- Fase 2 -----------------------------------------------------------------------------------
from src.analisis import anios_para_significancia, cambio_total  # noqa: E402


def ar1(n: int, phi: float, semilla: int) -> np.ndarray:
    """Ruido con memoria (cada mes se parece al anterior), como el clima real."""
    rng = np.random.default_rng(semilla)
    e = rng.normal(0, 1, n)
    for i in range(1, n):
        e[i] += phi * e[i - 1]
    return e


@pytest.mark.parametrize("metodo", ["hamed_rao", "estacional"])
def test_mann_kendall_metodos_recuperan_tendencia(metodo):
    s = sintetica(0.3)
    if metodo == "hamed_rao":
        s = anomalias(s)
    r = mann_kendall(s, metodo=metodo)  # el estacional funciona sin quitar el ciclo
    assert r["tendencia"] == "subida"
    assert r["p_valor"] < 0.05
    assert r["pendiente_sen_decada"] == pytest.approx(0.3, abs=0.05)


def test_estacional_tolera_meses_faltantes():
    s = sintetica(-0.3)
    s.iloc[::7] = np.nan
    assert mann_kendall(s, metodo="estacional")["pendiente_sen_decada"] == pytest.approx(-0.3, abs=0.05)


def test_hamed_rao_es_mas_prudente_con_autocorrelacion():
    idx = pd.date_range("1984-01-01", periods=480, freq="MS")
    s = pd.Series(ar1(480, 0.8, semilla=3), index=idx)  # sin tendencia, mucha memoria
    assert mann_kendall(s, metodo="hamed_rao")["p_valor"] > mann_kendall(s)["p_valor"]


def test_metodo_invalido():
    with pytest.raises(ValueError):
        mann_kendall(sintetica(0.3), metodo="magia")


def test_n_efectivo():
    idx = pd.date_range("1984-01-01", periods=480, freq="MS")
    con_memoria = tendencia_ols(pd.Series(ar1(480, 0.8, semilla=4), index=idx))
    sin_memoria = tendencia_ols(anomalias(sintetica(0.3)))
    assert con_memoria["n_efectivo"] < 0.3 * 480  # phi 0.8 -> n*(0.2/1.8) ~ 53
    assert sin_memoria["n_efectivo"] > 0.8 * 480


def test_cambio_total():
    s = sintetica(0.3)  # 40 años, media ~15.6
    r = cambio_total(s, tendencia_ols(anomalias(s)))
    assert r["anios"] == pytest.approx(39.9, abs=0.1)
    assert r["cambio"] == pytest.approx(0.3 * 3.99, abs=0.2)
    assert r["porcentaje"] == pytest.approx(100 * r["cambio"] / s.mean())
    assert cambio_total(anomalias(s), {"pendiente_decada": 0.3})["porcentaje"] is None  # media ~0


def test_anios_para_significancia():
    # error = 0.4 / 3.92; z*error/pendiente = 2 -> n_total = 120 * 2^(2/3) = 190.5 -> 70.5 meses de más
    ols = {"pendiente_decada": 0.1, "ic_bajo": -0.1, "ic_alto": 0.3, "p_valor": 0.3, "n": 120}
    assert anios_para_significancia(ols) == pytest.approx(5.9, abs=0.05)
    assert anios_para_significancia({**ols, "p_valor": 0.01}) == 0
    assert anios_para_significancia({**ols, "pendiente_decada": 0.0}) is None


def test_veredicto_en_dos_idiomas():
    ols = {"pendiente_decada": -0.3, "ic_bajo": -0.4, "ic_alto": -0.2, "p_valor": 0.001, "n": 480}
    mk = {"tendencia": "x", "p_valor": 0.001, "pendiente_sen_decada": -0.3}
    assert veredicto(ols, mk, "mm")["texto"].startswith("It falls by about 0.30 mm per decade")
    assert veredicto(ols, mk, "mm", idioma="es")["texto"].startswith("Baja unos 0.30 mm por década")
    with pytest.raises(ValueError):
        veredicto(ols, mk, "mm", idioma="fr")
