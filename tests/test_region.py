"""Pruebas de la región: zonas, contorno del Marco Geoestadístico de INEGI y celdas de POWER con sus pesos."""

import math

import pytest

from src import region

NORTE = {"Encarnación de Díaz", "Lagos de Moreno", "Ojuelos de Jalisco", "San Diego de Alejandría",
         "San Juan de los Lagos", "Teocaltiche", "Unión de San Antonio", "Villa Hidalgo"}


def test_zonas_con_sus_municipios():
    assert set(region.ZONAS) == {"los-altos", "altos-norte", "altos-sur"}
    assert len(region.ZONAS["los-altos"]["municipios"]) == 20
    assert set(region.ZONAS["altos-norte"]["municipios"]) == NORTE
    assert len(region.ZONAS["altos-sur"]["municipios"]) == 12
    assert set(region.ZONAS["altos-norte"]["municipios"]) | set(region.ZONAS["altos-sur"]["municipios"]) \
        == set(region.ZONAS["los-altos"]["municipios"])
    for id_zona, zona in region.ZONAS.items():
        assert zona["id"] == id_zona and zona["nombre"]


def test_obtener_zona():
    assert region.obtener_zona("altos-sur")["nombre"] == "Altos Sur"
    with pytest.raises(ValueError, match="no existe"):
        region.obtener_zona("guadalajara")


def test_geojson_pequeno_y_de_inegi():
    assert region.ARCHIVO_REGION.stat().st_size < 1_000_000
    fuente = (region.ARCHIVO_REGION.parent / "fuente.md").read_text(encoding="utf-8")
    assert "Marco Geoestadístico" in fuente and "INEGI" in fuente


@pytest.mark.parametrize("id_zona, municipios", [("los-altos", 20), ("altos-norte", 8), ("altos-sur", 12)])
def test_contorno(id_zona, municipios):
    gj = region.contorno(id_zona)
    assert gj["type"] == "FeatureCollection"
    zona, *resto = gj["features"]
    assert zona["properties"] == {**zona["properties"], "tipo": "zona", "id": id_zona}
    assert zona["geometry"]["type"] in ("Polygon", "MultiPolygon")
    assert len(resto) == municipios
    assert {f["properties"]["nombre"] for f in resto} == set(region.ZONAS[id_zona]["municipios"])
    assert all(f["properties"]["cvegeo"].startswith("14") for f in resto)  # 14 = Jalisco


@pytest.mark.parametrize("nombre, lon, lat, zona_esperada", [
    ("Tepatitlán", -102.763, 20.817, "altos-sur"),
    ("Arandas", -102.346, 20.704, "altos-sur"),
    ("Lagos de Moreno", -101.928, 21.357, "altos-norte"),
    ("Guadalajara", -103.349, 20.659, None),
    ("Aguascalientes", -102.29, 21.88, None),
])
def test_cabeceras_caen_en_su_zona(nombre, lon, lat, zona_esperada):
    for id_zona in ("altos-norte", "altos-sur"):
        assert region.dentro(lon, lat, id_zona) == (id_zona == zona_esperada), nombre
    assert region.dentro(lon, lat, "los-altos") == (zona_esperada is not None)


@pytest.mark.parametrize("id_zona", list(region.ZONAS))
def test_celdas_pesos_suman_uno_y_estan_en_la_malla_de_power(id_zona):
    lista = region.celdas(id_zona)
    assert lista
    assert sum(c["peso"] for c in lista) == pytest.approx(1.0)
    assert all(c["peso"] > 0 for c in lista)
    for c in lista:
        assert (c["lat"] + 90) / 0.5 == pytest.approx(round((c["lat"] + 90) / 0.5))
        assert (c["lon"] + 180) / 0.625 == pytest.approx(round((c["lon"] + 180) / 0.625))
        assert 20 <= c["lat"] <= 22.5 and -103.5 <= c["lon"] <= -101


def test_celdas_de_la_region_combinan_las_de_norte_y_sur():
    """Peso en toda la región = mezcla de Norte y Sur según su área (con la misma malla fina)."""
    norte = {(c["lat"], c["lon"]): c["peso"] for c in region.celdas("altos-norte")}
    sur = {(c["lat"], c["lon"]): c["peso"] for c in region.celdas("altos-sur")}
    todo = {(c["lat"], c["lon"]): c["peso"] for c in region.celdas("los-altos")}
    assert set(todo) == set(norte) | set(sur)
    # fracción de Norte que resuelve todas las celdas a la vez (mínimos cuadrados con una incógnita)
    llaves = list(todo)
    a = [norte.get(k, 0) - sur.get(k, 0) for k in llaves]
    b = [todo[k] - sur.get(k, 0) for k in llaves]
    f = sum(x * y for x, y in zip(a, b)) / sum(x * x for x in a)
    assert 0.5 < f < 0.6  # Altos Norte es ~55 % del área (8,160 de 14,730 km²)
    for k in llaves:
        assert todo[k] == pytest.approx(f * norte.get(k, 0) + (1 - f) * sur.get(k, 0), abs=0.01)


def test_celda_de():
    assert region.celda_de(20.817, -102.763) == (21.0, -102.5)
    assert region.celda_de(21.357, -101.928) == (21.5, -101.875)
    assert not math.isnan(region.celda_de(0.24, 0.31)[0])


def test_celdas_de_un_municipio_suman_uno_y_estan_en_la_zona():
    from src import region
    zona = {(c["lat"], c["lon"]) for c in region.celdas("los-altos")}
    for nombre in ("Tepatitlán de Morelos", "Lagos de Moreno", "Villa Hidalgo"):
        celdas = region.celdas_municipio(nombre)
        assert abs(sum(c["peso"] for c in celdas) - 1) < 1e-9
        assert {(c["lat"], c["lon"]) for c in celdas} <= zona
