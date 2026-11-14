"""Índices de agua: acumulados de lluvia, sequía meteorológica (SPI) y estrés hídrico del suelo (fase Los Altos).

- Sequía meteorológica = llovió menos de lo normal para esa época del año (SPI, McKee y colegas, 1993).
- Estrés hídrico del suelo = la humedad del suelo está por debajo de lo normal para ese mes
  (anomalía estandarizada). No mide directamente el estrés de los cultivos.
Los meses sin dato quedan como NaN: nunca se cuentan como cero.
"""

import numpy as np
import pandas as pd
from scipy import stats

REFERENCIA = (1991, 2020)   # "lo normal": norma climatológica de la OMM
TEMPORADA = (6, 10)         # temporada de lluvias en Los Altos: junio a octubre
MIN_ANIOS_REF = 15          # años con dato en la referencia para confiar en "lo normal"
UMBRALES = ((-2.0, "extremo"), (-1.5, "severo"), (-1.0, "moderado"))
NOMBRES = {
    "es": {
        "spi": {"extremo": "Sequía extrema", "severo": "Sequía severa", "moderado": "Sequía moderada",
                "normal": "Normal", "humedo": "Más lluvia de lo normal", "sin-dato": "Sin dato"},
        "estres": {"extremo": "Déficit extremo", "severo": "Déficit severo", "moderado": "Déficit moderado",
                   "normal": "Normal", "humedo": "Más húmedo de lo normal", "sin-dato": "Sin dato"},
    },
    "en": {
        "spi": {"extremo": "Extreme drought", "severo": "Severe drought", "moderado": "Moderate drought",
                "normal": "Normal", "humedo": "Wetter than normal", "sin-dato": "No data"},
        "estres": {"extremo": "Extreme deficit", "severo": "Severe deficit", "moderado": "Moderate deficit",
                   "normal": "Normal", "humedo": "Wetter than normal", "sin-dato": "No data"},
    },
}


def _mensual(serie: pd.Series) -> pd.Series:
    """La serie en meses seguidos (los que falten quedan NaN), para que cada posición sea su mes."""
    if not isinstance(serie.index, pd.DatetimeIndex):
        raise ValueError("La serie debe tener fechas mensuales (DatetimeIndex).")
    return serie.astype(float).resample("MS").mean()


def _en_referencia(serie: pd.Series, referencia: tuple[int, int]) -> pd.Series:
    """Valores dentro del periodo de referencia; ValueError si hay muy pocos años con dato."""
    ref = serie[(serie.index.year >= referencia[0]) & (serie.index.year <= referencia[1])].dropna()
    anios = ref.index.year.nunique()
    if anios < MIN_ANIOS_REF:
        raise ValueError(f"El periodo de referencia {referencia[0]}–{referencia[1]} tiene solo {anios} años con "
                         f"datos; hacen falta al menos {MIN_ANIOS_REF} para saber qué es lo normal.")
    return ref


def acumulados(lluvia: pd.Series, temporada: tuple[int, int] = TEMPORADA) -> pd.DataFrame:
    """Lluvia total por año y en la temporada de lluvias, en mm. Si falta un mes, ese total queda NaN."""
    s = _mensual(lluvia)
    anios = range(s.index.year.min(), s.index.year.max() + 1)
    s = s.reindex(pd.date_range(f"{anios[0]}-01-01", f"{anios[-1]}-12-01", freq="MS"))
    meses = range(temporada[0], temporada[1] + 1)
    filas = []
    for anio in anios:
        del_anio = s[s.index.year == anio]
        de_temporada = del_anio[del_anio.index.month.isin(meses)]
        anual_ok, temp_ok = bool(del_anio.notna().all()), bool(de_temporada.notna().all())
        filas.append({"anio": anio,
                      "anual_mm": float(del_anio.sum()) if anual_ok else np.nan,
                      "temporada_mm": float(de_temporada.sum()) if temp_ok else np.nan,
                      "completo": anual_ok and temp_ok})
    return pd.DataFrame(filas).set_index("anio")


def spi(lluvia: pd.Series, escala: int = 3, referencia: tuple[int, int] = REFERENCIA) -> pd.Series:
    """Índice de Precipitación Estandarizado (SPI) mensual.

    Suma la lluvia de los últimos `escala` meses, ajusta una distribución gamma para cada mes del año
    con el periodo de referencia (tomando aparte la probabilidad de que no llueva nada) y convierte
    esa probabilidad a una escala normal: 0 = lo normal, -1 o menos = sequía.
    """
    if escala < 1:
        raise ValueError("La escala del SPI debe ser de al menos 1 mes.")
    suma = _mensual(lluvia).rolling(escala, min_periods=escala).sum()
    ref = _en_referencia(suma, referencia)
    resultado = pd.Series(np.nan, index=suma.index, name=f"spi{escala}")
    for mes in range(1, 13):
        x_ref = ref[ref.index.month == mes].to_numpy()
        if len(x_ref) < MIN_ANIOS_REF:
            continue
        ceros = float(np.mean(x_ref == 0))
        positivos = x_ref[x_ref > 0]
        if len(positivos) < 5:          # casi nunca llueve en ese mes: no hay forma de medir "menos de lo normal"
            continue
        forma, _, escala_g = stats.gamma.fit(positivos, floc=0)
        del_mes = suma[suma.index.month == mes]
        prob = ceros + (1 - ceros) * stats.gamma.cdf(del_mes.clip(lower=0), forma, loc=0, scale=escala_g)
        # ponytail: prob se recorta a (0.0001, 0.9999) -> SPI entre -3.7 y +3.7; suficiente para clasificar.
        valores = stats.norm.ppf(np.clip(prob, 1e-4, 1 - 1e-4))
        resultado[del_mes.index] = np.where(del_mes.notna(), valores, np.nan)
    return resultado


def estres_hidrico(humedad: pd.Series, referencia: tuple[int, int] = REFERENCIA) -> pd.Series:
    """Anomalía estandarizada de la humedad del suelo: cuántas desviaciones típicas está de lo normal para ese mes."""
    s = _mensual(humedad)
    ref = _en_referencia(s, referencia)
    media = ref.groupby(ref.index.month).mean()
    desv = ref.groupby(ref.index.month).std(ddof=1).replace(0, np.nan)
    z = (s - s.index.month.map(media).to_numpy()) / s.index.month.map(desv).to_numpy()
    return z.rename("estres_hidrico")


def categoria(valor: float, indice: str, idioma: str = "en") -> dict:
    """Categoría de un valor de SPI o de estrés hídrico: {nivel, nombre, en_deficit}."""
    if idioma not in NOMBRES:
        raise ValueError("El idioma debe ser 'en' o 'es'.")
    if indice not in NOMBRES[idioma]:
        raise ValueError("El índice debe ser 'spi' o 'estres'.")
    if valor is None or not np.isfinite(valor):
        nivel = "sin-dato"
    else:
        nivel = next((n for limite, n in UMBRALES if valor <= limite), "humedo" if valor >= 1 else "normal")
    return {"nivel": nivel, "nombre": NOMBRES[idioma][indice][nivel], "en_deficit": nivel in ("moderado", "severo", "extremo")}


def resumen_indice(serie: pd.Series, indice: str, ultimos_anios: int = 5, idioma: str = "en") -> dict:
    """Lo principal de un índice: meses en déficit, el peor periodo y el último valor.

    El peor periodo es la racha de meses seguidos en déficit (-1 o menos) con mayor intensidad acumulada.
    """
    s = _mensual(serie)
    validos = s.dropna()
    if validos.empty:
        raise ValueError("No hay valores del índice para resumir.")
    deficit = s <= -1.0
    desde = validos.index[-1] - pd.DateOffset(years=ultimos_anios) + pd.DateOffset(months=1)

    peor, peor_suma, inicio, suma = None, 0.0, None, 0.0
    for fecha, valor in s.items():
        if valor <= -1.0:
            inicio, suma = (inicio or fecha), suma + valor
            if suma < peor_suma:
                peor, peor_suma = (inicio, fecha), suma
        else:                            # un mes normal o sin dato corta la racha
            inicio, suma = None, 0.0

    ultimo = float(validos.iloc[-1])
    return {
        "meses_en_deficit": int(deficit.sum()),
        "meses_totales": int(len(validos)),
        "meses_en_deficit_ultimos": int(deficit[s.index >= desde].sum()),
        "peor_periodo": (peor[0].strftime("%Y-%m"), peor[1].strftime("%Y-%m")) if peor else None,
        "categoria_peor": categoria(float(s[peor[0]:peor[1]].min()), indice, idioma)["nombre"] if peor else None,
        "ultimo_mes": validos.index[-1].strftime("%Y-%m"),
        "valor_ultimo": round(ultimo, 2),
        "categoria_ultimo": categoria(ultimo, indice, idioma)["nombre"],
    }
