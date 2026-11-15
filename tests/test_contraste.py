import numpy as np
import pandas as pd

from src import contraste


def test_estaciones_por_zona():
    todas = contraste.estaciones("los-altos")
    norte, sur = contraste.estaciones("altos-norte"), contraste.estaciones("altos-sur")
    assert len(todas) == len(norte) + len(sur) >= 10
    assert set(norte["zona"]) == {"altos-norte"}
    assert todas["lat"].between(20.4, 22.1).all() and todas["lon"].between(-103.3, -101.4).all()


def test_lluvia_de_estaciones_es_mensual_y_creible():
    s = contraste.lluvia_estaciones("los-altos").dropna()
    assert len(s) > 300 and s.min() >= 0 and s.max() < 600
    julio, febrero = s[s.index.month == 7].mean(), s[s.index.month == 2].mean()
    assert julio > 5 * febrero  # temporada de lluvias


def test_comparar_lluvia():
    meses = pd.date_range("2001-01-01", "2010-12-01", freq="MS")
    est = pd.Series(np.tile([5, 2, 1, 1, 20, 150, 200, 180, 140, 50, 10, 6], 10), index=meses, dtype=float)
    est += np.repeat(np.arange(10) * 10, 12)  # cada año un poco distinto
    r = contraste.comparar_lluvia(est * 0.9, est)
    assert r["anios"] == 10 and abs(r["r_anual"] - 1) < 1e-9 and round(r["diferencia_pct"]) == -10
    assert contraste.comparar_lluvia(est.iloc[:30], est) is None  # menos de 5 años completos


def test_monitor_y_coincidencia():
    m = contraste.monitor("los-altos")
    assert (m["total"] == 20).all() and m["fraccion_sequia"].between(0, 1).all()
    assert m.index.min() == pd.Timestamp("2003-01-01") and m.index.is_unique
    assert m.loc["2011":"2012", "fraccion_sequia"].max() == 1  # sequía de 2011–2012: los 20 municipios

    meses = pd.date_range("2010-01-01", periods=4, freq="MS")
    spi = pd.Series([-1.5, -1.2, 0.3, -2.0], index=meses)
    oficial = pd.Series([0.8, 0.1, 0.9, 0.6], index=meses)
    c = contraste.comparar_sequia(spi, oficial)
    assert (c["meses"], c["meses_spi"], c["meses_oficial"], c["confirmados"]) == (4, 3, 3, 2)
    assert contraste.comparar_sequia(spi, oficial.iloc[:0]) is None
