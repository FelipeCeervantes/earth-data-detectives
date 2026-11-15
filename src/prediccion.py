"""Panorama a futuro: qué pasaría si sigue la tendencia y qué tan seguido ha habido sequía.

No es un pronóstico del tiempo: nadie puede decir hoy qué año será seco. Aquí solo se extiende la línea de
tendencia de los totales anuales (con su intervalo de predicción del 95 %, el rango donde caería un solo año)
y se calcula, con la frecuencia del pasado, la probabilidad de tener al menos un año con sequía.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

UMBRAL_SEQUIA = -1.0   # SPI de -1 o menos: sequía (igual que src.indices)
UMBRAL_SEVERA = -1.5
MIN_ANIOS = 8
MIN_MESES_SPI = 10     # un año cuenta si tiene al menos 10 meses con SPI (el SPI-6 empieza con huecos)


def anuales(serie: pd.Series, tipo: str) -> pd.Series:
    """Total anual (lluvia, mm) o promedio anual (humedad, %), solo de años con los 12 meses."""
    s = serie.dropna()
    grupos = s.groupby(s.index.year)
    valores = grupos.sum() if tipo == "lluvia" else grupos.mean()
    return valores[grupos.size() == 12].astype(float)


def proyectar(serie: pd.Series, tipo: str, hasta: int) -> dict:
    """Recta de los valores anuales y su extensión hasta `hasta`, con el intervalo de predicción del 95 %."""
    a = anuales(serie, tipo)
    if len(a) < MIN_ANIOS:
        raise ValueError(f"Hacen falta al menos {MIN_ANIOS} años completos para mirar a futuro.")
    anios = a.index.to_numpy(dtype=float)
    modelo = sm.OLS(a.to_numpy(), sm.add_constant(anios)).fit()
    futuros = np.arange(int(anios.max()) + 1, hasta + 1)
    if len(futuros) == 0:
        raise ValueError("El año a mirar debe ser posterior al último año con datos.")
    marco = modelo.get_prediction(sm.add_constant(futuros.astype(float), has_constant="add")).summary_frame(alpha=0.05)
    futuro = pd.DataFrame({"media": marco["mean"].to_numpy(), "bajo": marco["obs_ci_lower"].to_numpy(),
                           "alto": marco["obs_ci_upper"].to_numpy()}, index=futuros)
    if tipo != "lluvia":  # la humedad es un % de saturación: el rango no puede salir de 0 a 100
        futuro = futuro.clip(0, 100)
    else:
        futuro = futuro.clip(lower=0)
    return {"observado": a, "ajuste": pd.Series(modelo.fittedvalues, index=a.index), "futuro": futuro,
            "pendiente_decada": float(modelo.params[1] * 10), "p_valor": float(modelo.pvalues[1]),
            "promedio": float(a.mean()), "anio_meta": int(futuros[-1])}


def probabilidad_sequia(spi: pd.Series, anios_adelante: tuple[int, ...] = (5, 10)) -> dict:
    """Con qué frecuencia hubo al menos un mes de sequía por año, y la probabilidad de tener al menos un año así
    en los próximos años si el pasado se repite (cada año se toma como independiente)."""
    s = spi.dropna()
    grupos = s.groupby(s.index.year)
    minimos = grupos.min()[grupos.size() >= MIN_MESES_SPI]
    if len(minimos) < MIN_ANIOS:
        raise ValueError(f"Hacen falta al menos {MIN_ANIOS} años con SPI para calcular probabilidades.")
    con_sequia = minimos <= UMBRAL_SEQUIA
    p = float(con_sequia.mean())
    p_severa = float((minimos <= UMBRAL_SEVERA).mean())
    mitad = len(con_sequia) // 2
    p_tendencia = None
    if 0 < con_sequia.sum() < len(con_sequia):  # con todos iguales no hay tendencia que medir
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                logit = sm.Logit(con_sequia.astype(float).to_numpy(),
                                 sm.add_constant(minimos.index.to_numpy(dtype=float))).fit(disp=0)
                p_tendencia = float(logit.pvalues[1])
                sube = bool(logit.params[1] > 0)
            except Exception:  # separación perfecta u otro problema numérico: no se reporta tendencia
                p_tendencia, sube = None, False
    return {"minimos": minimos, "con_sequia": con_sequia, "anios": len(minimos), "anios_sequia": int(con_sequia.sum()),
            "p_anual": p, "p_severa": p_severa,
            "probabilidad": {n: 1 - (1 - p) ** n for n in anios_adelante},
            "probabilidad_severa": {n: 1 - (1 - p_severa) ** n for n in anios_adelante},
            "cada_cuantos_severa": (1 / p_severa) if p_severa > 0 else None,
            "primera_mitad": float(con_sequia.iloc[:mitad].mean()), "segunda_mitad": float(con_sequia.iloc[mitad:].mean()),
            "p_tendencia": p_tendencia, "mas_frecuentes": sube if p_tendencia is not None else None}
