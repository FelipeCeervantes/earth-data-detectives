"""Pruebas del catálogo de la fase Los Altos: solo lluvia y las 3 capas de humedad del suelo."""

import pytest

from src import catalogo
from src.catalogo import VARIABLES, listar_variables, obtener_variable

CAMPOS = {"id", "nombre", "definicion", "unidades", "fuente", "parametro_power", "anio_inicio", "anio_fin", "tipo"}
ESPERADAS = {
    "precipitacion": ("PRECTOTCORR", "mm/mes", "lluvia"),
    "humedad_superficie": ("GWETTOP", "% de saturación", "humedad"),
    "humedad_raices": ("GWETROOT", "% de saturación", "humedad"),
    "humedad_perfil": ("GWETPROF", "% de saturación", "humedad"),
}


def test_solo_lluvia_y_tres_capas_de_humedad():
    assert set(VARIABLES) == set(ESPERADAS)
    for id_var, var in VARIABLES.items():
        assert set(var) == CAMPOS
        assert var["id"] == id_var
        assert (var["parametro_power"], var["unidades"], var["tipo"]) == ESPERADAS[id_var]
        assert (var["anio_inicio"], var["anio_fin"]) == (1981, 2024)
        assert "POWER" in var["fuente"]
        assert len(var["definicion"]) > 40  # una explicación de verdad, no una etiqueta


def test_sin_ciudades():
    assert not hasattr(catalogo, "CIUDADES")


def test_listar_variables_regresa_copias():
    lista = listar_variables()
    assert [v["id"] for v in lista] == list(VARIABLES)
    lista[0]["nombre"] = "cambiado"
    assert VARIABLES[lista[0]["id"]]["nombre"] != "cambiado"


def test_obtener_variable():
    assert obtener_variable("humedad_raices")["parametro_power"] == "GWETROOT"
    with pytest.raises(ValueError, match="no existe"):
        obtener_variable("temperatura")
