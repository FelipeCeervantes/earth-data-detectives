"""Análisis: anomalías mensuales, OLS por década con IC 95%, Mann-Kendall y pendiente de Sen (Fase 1 y 2)."""

import numpy as np
import pandas as pd
import pymannkendall as pmk
import statsmodels.api as sm
from scipy.stats import theilslopes


ALFA = 0.05
MIN_MESES = 24


def anomalias(serie: pd.Series) -> pd.Series:
    """Resta a cada valor la media de su mes del año (quita el ciclo estacional)."""
    return serie - serie.groupby(serie.index.month).transform("mean")


def _decadas(serie: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Tiempo en décadas (desde el primer dato) y valores, sin meses faltantes."""
    s = serie.dropna()
    if len(s) < MIN_MESES:
        raise ValueError(f"Hacen falta al menos {MIN_MESES} meses con datos; hay {len(s)}.")
    anios = s.index.year + (s.index.month - 1) / 12
    return np.asarray((anios - anios[0]) / 10, dtype=float), s.to_numpy(dtype=float)


def tendencia_ols(serie: pd.Series) -> dict:
    """Regresión lineal: pendiente por década con IC 95%, p-valor y n efectivo."""
    x, y = _decadas(serie)
    # Errores HAC (12 rezagos): el IC y el p-valor ya toman en cuenta la autocorrelación mensual.
    ajuste = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    bajo, alto = ajuste.conf_int(alpha=ALFA)[1]
    r1 = float(np.corrcoef(ajuste.resid[:-1], ajuste.resid[1:])[0, 1])  # autocorrelación de un mes
    n_efectivo = len(y) * (1 - r1) / (1 + r1)
    return {
        "pendiente_decada": float(ajuste.params[1]),
        "ic_bajo": float(bajo),
        "ic_alto": float(alto),
        "p_valor": float(ajuste.pvalues[1]),
        "n": len(y),
        "n_efectivo": int(np.clip(round(n_efectivo), 2, len(y))),
    }


def mann_kendall(serie: pd.Series, metodo: str = "original") -> dict:
    """Mann-Kendall y pendiente de Sen por década (tolera meses faltantes).

    metodo: "original"; "hamed_rao" (corrige el p-valor por la autocorrelación);
    "estacional" (compara cada mes con el mismo mes de otros años; sirve también sin quitar el ciclo).
    """
    x, y = _decadas(serie)
    if metodo == "original":
        mk = pmk.original_test(y, alpha=ALFA)
        pendiente = theilslopes(y, x)[0]
    elif metodo == "hamed_rao":
        mk = pmk.hamed_rao_modification_test(y, alpha=ALFA)
        pendiente = theilslopes(y, x)[0]
    elif metodo == "estacional":
        mensual = serie.resample("MS").mean()  # meses faltantes como NaN para que cada posición sea su mes
        mk = pmk.seasonal_test(mensual.to_numpy(dtype=float), period=12, alpha=ALFA)
        pendiente = mk.slope * 10  # pymannkendall la da por año
    else:
        raise ValueError(f"Método '{metodo}' no válido: usa original, hamed_rao o estacional.")
    tendencia = {"increasing": "subida", "decreasing": "bajada"}.get(mk.trend, "sin tendencia")
    return {
        "tendencia": tendencia,
        "p_valor": float(mk.p),
        "pendiente_sen_decada": float(pendiente),
    }


def cambio_total(serie: pd.Series, ols: dict) -> dict:
    """Cambio en todo el periodo según la tendencia, en unidades y en % de la media.

    `serie` son los valores reales (no las anomalías), para que el % tenga sentido.
    El % solo se da si la media es positiva; en °C no se debe mostrar (0 °C no es "nada").
    """
    x, _ = _decadas(serie)
    cambio = ols["pendiente_decada"] * (x[-1] - x[0])
    media = float(serie.mean())
    return {
        "cambio": float(cambio),
        "porcentaje": float(100 * cambio / media) if media > 0 else None,
        "anios": round(float(x[-1] - x[0]) * 10, 1),
    }


def anios_para_significancia(ols: dict) -> float | None:
    """Años de datos de más que harían falta para que la tendencia sea significativa si siguiera igual.

    0 si ya lo es; None si la pendiente es 0. El error de la pendiente baja como n^(-3/2).
    """
    if ols["p_valor"] < ALFA:
        return 0.0
    pendiente = abs(ols["pendiente_decada"])
    if pendiente == 0:
        return None
    z = 1.96
    error = (ols["ic_alto"] - ols["ic_bajo"]) / (2 * z)
    # ponytail: aproximación con ruido constante; no sustituye una prueba con datos nuevos.
    n_total = ols["n"] * (z * error / pendiente) ** (2 / 3)
    return round(max(n_total - ols["n"], 0) / 12, 1)


VEREDICTOS = {   # campos: {pendiente} (valor absoluto), {bajo}, {alto}, {unidades}
    "es": {
        "rojo": ("Sube unos {pendiente:.2f} {unidades} por década (IC 95 %: {bajo:.2f} a {alto:.2f}). "
                 "Las dos pruebas coinciden: es muy poco probable que sea casualidad."),
        "verde": ("Baja unos {pendiente:.2f} {unidades} por década (IC 95 %: {bajo:.2f} a {alto:.2f}). "
                  "Las dos pruebas coinciden: es muy poco probable que sea casualidad."),
        "amarillo": ("Hay indicios de cambio, pero solo una de las dos pruebas lo confirma. "
                     "Todavía no se puede afirmar que haya una tendencia."),
        "gris": "No se ve una tendencia clara en este periodo: los cambios caben dentro de la variación normal.",
    },
    "en": {
        "rojo": ("It rises by about {pendiente:.2f} {unidades} per decade (95% CI: {bajo:.2f} to {alto:.2f}). "
                 "Both tests agree: it is very unlikely to be chance."),
        "verde": ("It falls by about {pendiente:.2f} {unidades} per decade (95% CI: {bajo:.2f} to {alto:.2f}). "
                  "Both tests agree: it is very unlikely to be chance."),
        "amarillo": ("There are signs of change, but only one of the two tests confirms it. "
                     "We cannot say yet that there is a trend."),
        "gris": "There is no clear trend in this period: the changes fit within normal variation.",
    },
}


def _frases(idioma: str) -> dict:
    if idioma not in VEREDICTOS:
        raise ValueError("El idioma debe ser 'en' o 'es'.")
    return VEREDICTOS[idioma]


def veredicto(ols: dict, mk: dict, unidades: str, idioma: str = "en") -> dict:
    """Une OLS y Mann-Kendall en un texto sencillo y un color.

    rojo = sube y las dos pruebas coinciden; verde = baja y coinciden;
    amarillo = solo una prueba la ve (no concluyente); gris = ninguna la ve.
    El color marca la dirección, no si el cambio es bueno o malo. `idioma`: "en" (por defecto) o "es".
    """
    sig_ols = ols["p_valor"] < ALFA
    sig_mk = mk["p_valor"] < ALFA
    datos = {
        "pendiente": abs(ols["pendiente_decada"]),
        "bajo": ols["ic_bajo"],
        "alto": ols["ic_alto"],
        "unidades": unidades,
    }
    if sig_ols and sig_mk and np.sign(ols["pendiente_decada"]) == np.sign(mk["pendiente_sen_decada"]):
        if ols["pendiente_decada"] > 0:
            return {"texto": _frases(idioma)["rojo"].format(**datos), "color": "rojo"}
        return {"texto": _frases(idioma)["verde"].format(**datos), "color": "verde"}
    if sig_ols or sig_mk:
        return {"texto": _frases(idioma)["amarillo"].format(**datos), "color": "amarillo"}
    return {"texto": _frases(idioma)["gris"].format(**datos), "color": "gris"}
