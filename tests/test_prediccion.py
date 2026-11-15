import numpy as np
import pandas as pd
import pytest

from src import prediccion as P

MESES = pd.date_range("1991-01-01", "2024-12-01", freq="MS")


def test_anuales_solo_cuenta_anios_completos():
    s = pd.Series(10.0, index=MESES)
    s.iloc[5] = np.nan  # a 1991 le falta un mes
    a = P.anuales(s, "lluvia")
    assert 1991 not in a.index and a.loc[1992] == 120
    assert P.anuales(s, "humedad").loc[1992] == 10


def test_proyectar_sigue_la_recta_y_da_un_rango():
    anio = MESES.year.to_numpy()
    s = pd.Series(50 + (anio - 1991) * 0.1, index=MESES) + np.random.default_rng(1).normal(0, 3, len(MESES))
    r = P.proyectar(s, "lluvia", 2030)
    assert r["anio_meta"] == 2030 and list(r["futuro"].index) == list(range(2025, 2031))
    assert r["pendiente_decada"] == pytest.approx(12, abs=1.5)  # 0.1 mm/mes por año = 1.2 mm/año = 12 por década
    assert r["p_valor"] < 0.05
    fila = r["futuro"].loc[2030]
    assert fila["bajo"] < fila["media"] < fila["alto"]
    with pytest.raises(ValueError):
        P.proyectar(s.loc["2020":], "lluvia", 2030)  # menos de 8 años


def test_probabilidad_de_sequia():
    anios = range(1991, 2021)  # 30 años; uno de cada tres con un mes de sequía (y uno de cada seis, severa)
    valores = []
    for i, a in enumerate(anios):
        minimo = -1.8 if i % 6 == 0 else (-1.2 if i % 3 == 0 else 0.2)
        valores += [minimo] + [0.5] * 11
    spi = pd.Series(valores, index=pd.date_range("1991-01-01", "2020-12-01", freq="MS"))
    r = P.probabilidad_sequia(spi)
    assert r["anios"] == 30 and r["anios_sequia"] == 10
    assert r["p_anual"] == pytest.approx(1 / 3)
    assert r["probabilidad"][5] == pytest.approx(1 - (2 / 3) ** 5)
    assert r["cada_cuantos_severa"] == pytest.approx(6)
    assert r["p_tendencia"] is None or r["p_tendencia"] > 0.05  # repartidas parejo: sin tendencia
