"""Pruebas de la descarga de NASA POWER para Los Altos. Las de red llevan @pytest.mark.red."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import datos, region
from src.catalogo import VARIABLES

EJEMPLO = Path(__file__).parent / "datos_ejemplo" / "power_altos_2020.json"


@pytest.fixture
def sin_red(tmp_path, monkeypatch):
    """Caché en una carpeta de prueba y POWER simulado con el JSON de ejemplo."""
    monkeypatch.setattr(datos, "CARPETA_DATOS", tmp_path / "data")
    monkeypatch.setattr(datos, "CARPETA_DEMOS", tmp_path / "demos")
    llamadas = []

    def falso(params):
        llamadas.append(params)
        return json.loads(EJEMPLO.read_text(encoding="utf-8"))

    monkeypatch.setattr(datos, "_pedir_json", falso)
    return llamadas


@pytest.fixture
def red_caida(tmp_path, monkeypatch):
    monkeypatch.setattr(datos, "CARPETA_DATOS", tmp_path / "data")
    monkeypatch.setattr(datos, "CARPETA_DEMOS", tmp_path / "demos")

    def caido(params):
        raise ConnectionError("No se pudo descargar de NASA POWER: sin red (simulado)")

    monkeypatch.setattr(datos, "_pedir_json", caido)
    return tmp_path / "demos"


# --- unidades ------------------------------------------------------------------------------

def test_lluvia_pasa_a_mm_por_mes_con_los_dias_de_cada_mes():
    idx = pd.DatetimeIndex(["2020-02-01", "2021-02-01", "2020-07-01"])  # 29, 28 y 31 días
    mm_dia = pd.Series([1.0, 1.0, np.nan], index=idx)
    mm_mes = datos.a_unidades_app(mm_dia, "lluvia")
    assert mm_mes.iloc[0] == 29 and mm_mes.iloc[1] == 28
    assert np.isnan(mm_mes.iloc[2])  # NaN se queda NaN, nunca 0


def test_humedad_pasa_a_porcentaje_de_saturacion():
    s = pd.Series([0.0, 0.5, 1.0], index=pd.date_range("2020-01-01", periods=3, freq="MS"))
    assert list(datos.a_unidades_app(s, "humedad")) == [0.0, 50.0, 100.0]


def test_serie_punto_limpia_y_en_unidades_de_la_app(sin_red):
    lluvia = datos.serie_punto("precipitacion", 21.0, -102.5, 2020, 2020)
    assert len(lluvia) == 12 and (lluvia.index.day == 1).all()  # sin el mes 13
    assert lluvia.name == "precipitacion" and lluvia.dtype == float
    assert lluvia[pd.Timestamp("2020-02-01")] == pytest.approx(1.0 * 29)  # 2020 es bisiesto
    assert lluvia[pd.Timestamp("2020-06-01")] == pytest.approx(5.0 * 30)
    assert lluvia[pd.Timestamp("2020-03-01")] == 0.0  # un cero real se queda en cero
    assert np.isnan(lluvia[pd.Timestamp("2020-07-01")])  # -999 → NaN
    assert set(sin_red[0]["parameters"].split(",")) == {"PRECTOTCORR", "GWETTOP", "GWETROOT", "GWETPROF"}

    humedad = datos.serie_punto("humedad_superficie", 21.0, -102.5, 2020, 2020)
    assert len(sin_red) == 1  # la humedad de esa celda llegó en la misma petición y salió de la caché
    assert humedad.name == "humedad_superficie"
    assert humedad[pd.Timestamp("2020-01-01")] == pytest.approx(52.0)
    assert np.isnan(humedad[pd.Timestamp("2020-08-01")])
    assert humedad.max() <= 100


def test_segunda_llamada_sale_de_la_cache(sin_red, monkeypatch):
    primera = datos.serie_punto("precipitacion", 21.0, -102.5, 2020, 2020)

    def sin_internet(params):
        raise AssertionError("No debería llamar a internet: ya está en caché")

    monkeypatch.setattr(datos, "_pedir_json", sin_internet)
    pd.testing.assert_series_equal(primera, datos.serie_punto("precipitacion", 21.0, -102.5, 2020, 2020),
                                   check_freq=False)
    assert len(sin_red) == 1


# --- promedio ponderado de la zona ---------------------------------------------------------

def test_promedio_ponderado_y_regla_de_la_mitad_del_peso():
    idx = pd.date_range("2020-01-01", periods=3, freq="MS")
    a = pd.Series([10.0, np.nan, np.nan], index=idx)
    b = pd.Series([20.0, 20.0, np.nan], index=idx)
    c = pd.Series([40.0, 40.0, 40.0], index=idx)
    s = datos.promedio_ponderado([a, b, c], [0.5, 0.3, 0.2], "precipitacion")
    assert s.iloc[0] == pytest.approx(0.5 * 10 + 0.3 * 20 + 0.2 * 40)
    assert np.isnan(s.iloc[1])  # falta la mitad del peso (0.5): NaN
    assert np.isnan(s.iloc[2])  # falta el 80 %
    s2 = datos.promedio_ponderado([a, b, c], [0.2, 0.5, 0.3], "precipitacion")
    assert s2.iloc[1] == pytest.approx((0.5 * 20 + 0.3 * 40) / 0.8)  # falta 20 %: se reparte entre las demás


def test_serie_zona_es_el_promedio_ponderado_de_sus_celdas(monkeypatch):
    idx = pd.date_range("2020-01-01", periods=12, freq="MS")
    valor = {}

    def falso(id_variable, lat, lon, a0, a1):
        valor[(lat, lon)] = lat * 10 + lon  # cada celda con un valor distinto
        return pd.Series(valor[(lat, lon)], index=idx, name=id_variable)

    monkeypatch.setattr(datos, "serie_punto", falso)
    monkeypatch.setattr(datos, "USAR_GUARDADOS", False)  # que no salga de demos/: queremos ver el promedio
    s = datos.serie_zona("humedad_raices", "altos-sur", 2020, 2020)
    esperado = sum(c["peso"] * (c["lat"] * 10 + c["lon"]) for c in region.celdas("altos-sur"))
    assert s.name == "humedad_raices" and len(s) == 12
    assert s.iloc[0] == pytest.approx(esperado)
    assert len(valor) == len(region.celdas("altos-sur"))


# --- primero lo guardado en demos/, y sin internet ----------------------------------------

def test_la_zona_sale_primero_de_demos_sin_descargar(red_caida, recwarn):
    fechas = pd.date_range("1981-01-01", "2024-12-01", freq="MS")
    red_caida.mkdir()
    pd.Series(np.linspace(10, 90, len(fechas)), index=fechas, name="precipitacion").to_csv(
        datos.ruta_demo("precipitacion", "altos-norte"), header=True)
    s = datos.serie_zona("precipitacion", "altos-norte", 2001, 2024)  # la red está caída: no la toca
    assert (s.index[0], s.index[-1]) == (pd.Timestamp("2001-01-01"), pd.Timestamp("2024-12-01"))
    assert len(s) == 24 * 12 and s.name == "precipitacion"
    assert not [w for w in recwarn if "Sin conexión" in str(w.message)]  # no es una falla: es lo normal


def test_cada_celda_sale_primero_de_demos(red_caida):
    fechas = pd.date_range("1981-01-01", "2024-12-01", freq="MS")
    red_caida.mkdir()
    tabla = pd.DataFrame({datos.columna_celda(c["lat"], c["lon"]): float(i) for i, c in enumerate(region.celdas("altos-sur"))},
                         index=fechas)
    tabla.to_csv(datos.ruta_demo_celdas("humedad_perfil"))
    s = datos.serie_zona("humedad_perfil", "altos-sur", 2001, 2024)
    esperado = sum(c["peso"] * i for i, c in enumerate(region.celdas("altos-sur")))
    assert s.iloc[0] == pytest.approx(esperado) and s.name == "humedad_perfil"


def test_si_lo_guardado_no_cubre_el_periodo_se_descarga(sin_red):
    fechas = pd.date_range("1981-01-01", "2010-12-01", freq="MS")  # le faltan años
    datos.CARPETA_DEMOS.mkdir(parents=True)
    pd.DataFrame({datos.columna_celda(21.0, -102.5): 1.0}, index=fechas).to_csv(
        datos.ruta_demo_celdas("precipitacion"))
    s = datos.serie_punto("precipitacion", 21.0, -102.5, 2020, 2020)
    assert len(sin_red) == 1 and s[pd.Timestamp("2020-02-01")] == pytest.approx(29.0)


def test_generar_demos_puede_ignorar_lo_guardado(sin_red, monkeypatch):
    fechas = pd.date_range("1981-01-01", "2024-12-01", freq="MS")
    datos.CARPETA_DEMOS.mkdir(parents=True)
    pd.DataFrame({datos.columna_celda(21.0, -102.5): 1.0}, index=fechas).to_csv(
        datos.ruta_demo_celdas("precipitacion"))
    monkeypatch.setattr(datos, "USAR_GUARDADOS", False)
    datos.serie_punto("precipitacion", 21.0, -102.5, 2020, 2020)
    assert len(sin_red) == 1  # descargó aunque había datos guardados


def test_sin_red_y_sin_lo_guardado_avisa_y_usa_la_zona(red_caida, monkeypatch):
    """Si las celdas no están guardadas pero la zona sí, y no hay red: usa la zona y avisa."""
    fechas = pd.date_range("1981-01-01", "2024-12-01", freq="MS")
    red_caida.mkdir()
    pd.Series(5.0, index=fechas, name="humedad_raices").to_csv(datos.ruta_demo("humedad_raices", "altos-sur"),
                                                               header=True)
    monkeypatch.setattr(datos, "_cubre", lambda serie, a0, a1: False)  # como si lo guardado no alcanzara
    with pytest.warns(UserWarning, match="Sin conexión con NASA POWER"):
        s = datos.serie_zona("humedad_raices", "altos-sur", 2001, 2024)
    assert len(s) == 24 * 12


def test_sin_red_ni_respaldo_lanza_connection_error(red_caida):
    with pytest.raises(ConnectionError):
        datos.serie_zona("precipitacion", "altos-sur", 2001, 2024)
    with pytest.raises(ConnectionError):
        datos.serie_punto("precipitacion", 21.0, -102.5, 2001, 2024)


def test_respaldo_en_demos_para_3_zonas_y_4_variables():
    for id_variable, var in VARIABLES.items():
        for id_zona in region.ZONAS:
            ruta = datos.ruta_demo(id_variable, id_zona)
            assert ruta.exists(), ruta.name
            s = datos._leer_csv(ruta, id_variable)
            assert (s.index[0], s.index[-1]) == (pd.Timestamp("1981-01-01"), pd.Timestamp("2024-12-01"))
            if var["tipo"] == "lluvia":
                anual = s.groupby(s.index.year).sum()
                assert 300 < anual.median() < 1500  # mm al año, razonable para Los Altos
            else:
                assert 0 <= s.min() and s.max() <= 100
    assert not list(datos.CARPETA_DEMOS.glob("power_temperatura_*.csv"))  # ya no hay respaldos de ciudades
    for id_variable in VARIABLES:  # y cada celda de la región, para el mapa
        tabla = pd.read_csv(datos.ruta_demo_celdas(id_variable), index_col=0)
        assert set(tabla.columns) == {datos.columna_celda(c["lat"], c["lon"]) for c in region.celdas("los-altos")}


# --- entradas inválidas --------------------------------------------------------------------

@pytest.mark.parametrize("args", [
    ("temperatura", "los-altos", 2001, 2024),
    ("precipitacion", "guadalajara", 2001, 2024),
    ("precipitacion", "los-altos", 1970, 2024),
    ("precipitacion", "los-altos", 2024, 2001),
])
def test_entradas_invalidas(sin_red, args):
    with pytest.raises(ValueError):
        datos.serie_zona(*args)
    assert sin_red == []


@pytest.mark.red
def test_descarga_real(tmp_path, monkeypatch):
    monkeypatch.setattr(datos, "CARPETA_DATOS", tmp_path)
    s = datos.serie_punto("precipitacion", 21.0, -102.5, 2020, 2020)
    assert len(s) == 12 and s.notna().all()
    assert 300 < s.sum() < 1500  # mm en el año
