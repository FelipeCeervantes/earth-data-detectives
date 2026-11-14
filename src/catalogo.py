"""Catálogo de variables de la fase Los Altos: lluvia y humedad del suelo (NASA POWER, MERRA-2).

Las unidades son las que entrega src/datos.py ya convertidas:
lluvia en mm por mes y humedad del suelo en % de saturación.
"""

from __future__ import annotations

from copy import deepcopy

# POWER mensual tiene datos desde 1981; el último año completo disponible.
ANIO_INICIO_POWER = 1981
ANIO_FIN_POWER = 2024

_HUMEDAD_COMUN = (
    " Se mide como porcentaje de saturación: 0 % es tierra completamente seca y 100 % es tierra con todos "
    "sus poros llenos de agua."
)

_VARIABLES_BASE = [
    {
        "id": "precipitacion",
        "nombre": "Lluvia",
        "definicion": "Cuánta agua cayó del cielo en el mes (lluvia, granizo o nieve). 1 mm equivale a 1 litro "
                      "de agua por cada metro cuadrado de suelo.",
        "unidades": "mm/mes",
        "fuente": "MERRA-2 vía NASA POWER (precipitación corregida)",
        "parametro_power": "PRECTOTCORR",
        "tipo": "lluvia",
    },
    {
        "id": "humedad_superficie",
        "nombre": "Humedad del suelo en la superficie",
        "definicion": "Qué tan mojados están los primeros 5 centímetros del suelo. Cambia rápido: sube con "
                      "cada lluvia y baja en pocos días de sol." + _HUMEDAD_COMUN,
        "unidades": "% de saturación",
        "fuente": "MERRA-2 vía NASA POWER",
        "parametro_power": "GWETTOP",
        "tipo": "humedad",
    },
    {
        "id": "humedad_raices",
        "nombre": "Humedad del suelo en la zona de raíces",
        "definicion": "Qué tan mojado está el suelo donde están las raíces de las plantas (hasta 1 metro de "
                      "profundidad). Es el agua que pueden aprovechar los cultivos y los pastos." + _HUMEDAD_COMUN,
        "unidades": "% de saturación",
        "fuente": "MERRA-2 vía NASA POWER",
        "parametro_power": "GWETROOT",
        "tipo": "humedad",
    },
    {
        "id": "humedad_perfil",
        "nombre": "Humedad del suelo en todo el perfil",
        "definicion": "Qué tan mojado está el suelo desde la superficie hasta la roca. Cambia lento: guarda la "
                      "memoria de varios meses de lluvia o de sequía." + _HUMEDAD_COMUN,
        "unidades": "% de saturación",
        "fuente": "MERRA-2 vía NASA POWER",
        "parametro_power": "GWETPROF",
        "tipo": "humedad",
    },
]

VARIABLES: dict[str, dict] = {
    v["id"]: {**v, "anio_inicio": ANIO_INICIO_POWER, "anio_fin": ANIO_FIN_POWER}
    for v in _VARIABLES_BASE
}


def listar_variables() -> list[dict]:
    """Regresa la lista de variables (copias, para que nadie modifique el catálogo)."""
    return [deepcopy(v) for v in VARIABLES.values()]


def obtener_variable(id_variable: str) -> dict:
    """Regresa la variable con ese id. Lanza ValueError si no existe."""
    if id_variable not in VARIABLES:
        validas = ", ".join(VARIABLES)
        raise ValueError(f"La variable '{id_variable}' no existe. Usa una de: {validas}.")
    return deepcopy(VARIABLES[id_variable])
