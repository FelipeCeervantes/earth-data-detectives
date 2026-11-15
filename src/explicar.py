"""Resumen en palabras sencillas de los resultados de Los Altos: con plantillas y, si hay clave, con Gemini.

Gemini SOLO explica resultados que Python ya calculó (`resultados()`); nunca calcula ni inventa cifras.
Si Gemini menciona un número que no viene en los resultados, su respuesta se descarta y se usa el
resumen con plantillas. Sin clave o si la API falla, la app sigue funcionando.
"""

from __future__ import annotations

import json
import os
import re

import pandas as pd
import requests

from src.analisis import anios_para_significancia, anomalias, mann_kendall, tendencia_ols, veredicto
from src.indices import REFERENCIA, acumulados, estres_hidrico, resumen_indice, spi

# Modelo e instrucciones de la tarea manual 09 (compañero de Gemini, Google AI Studio).
MODELO = os.environ.get("GEMINI_MODELO", "gemini-4-hydrogen")
RESPALDO = "gemini-2.5-flash"   # si el modelo principal no responde (p. ej. HTTP 503, saturado)
URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
TIMEOUT_S = 30
REINTENTOS = 2
IDIOMA_EN = ("\n\nIMPORTANTE DE IDIOMA: Redacta los valores de texto en inglés claro y sencillo (manteniendo "
             "exactamente las mismas claves JSON y los valores permitidos del enum \"tema\": lluvia, sequia, humedad, "
             "estres, donde).")
PALABRA = {"rojo": "sube", "verde": "baja", "amarillo": "no concluyente", "gris": "sin tendencia"}
MIN_ANIOS_TENDENCIA = 10    # con menos años, una "tendencia" es puro ruido y no se reporta
TEMAS = ("lluvia", "sequia", "humedad", "estres", "donde")

INSTRUCCIONES = """Eres el intérprete de datos de "Detectives de Datos de la Tierra", una API que resume, explica y analiza resultados estadísticos sobre lluvia (sequía meteorológica / SPI) y humedad del suelo (estrés hídrico del suelo) en Los Altos de Jalisco, México (20 municipios). Tu trabajo es explicar resultados que el software YA calculó, para personas sin formación científica: estudiantes, productores y público en general.

Recibirás un JSON con resultados (y opcionalmente una consulta específica sobre esos datos). Sigue estas reglas siempre:
1. Usa SOLO cifras, fechas, lugares y nombres que aparecen en el JSON. No calcules nada nuevo, no inventes datos, fuentes ni causas, y no redondees de forma que cambie el sentido.
2. Si un dato falta o es null, dilo con claridad ("no hay datos suficientes para…"). Nunca lo supongas.
3. Llama "clara" o "significativa" a una tendencia SOLO si su veredicto es "sube" o "baja". Si es "no concluyente" o "sin tendencia", preséntalo como un resultado válido y, si viene "anios_para_significancia", di cuántos años más de datos harían falta para estar seguros.
4. Sequía meteorológica (SPI) significa que llovió menos de lo normal para esa época del año. No es lo mismo que falta de agua en el suelo ni en los cultivos.
5. Estrés hídrico del suelo significa aquí que la humedad del suelo estuvo por debajo de lo normal para ese mes. No afirmes que los cultivos sufrieron estrés: para eso se necesitan otros datos.
6. No atribuyas los cambios a ninguna causa (agave, deforestación, cambio climático, riego, etc.), aunque el usuario lo sugiera. Puedes decir que conocer las causas requiere otros estudios.
7. Menciona en lenguaje sencillo la incertidumbre y las limitaciones que vengan en el JSON (por ejemplo, que cada dato cubre unos 50 km o que viene de un modelo) dentro de "cuidado".
8. Tono claro y tranquilo, sin alarmismo y sin tecnicismos. Si usas un término técnico (p-valor, SPI, tendencia, anomalía), explícalo en una frase.
9. Responde en español de México (a menos que se indique explícitamente idioma inglés), solo con el JSON del formato indicado, sin texto fuera de él. Respeta estrictamente los límites de palabras: "titular" máximo 12 palabras; "resumen" 2 o 3 oraciones con máximo 60 palabras en total; cada "texto" en "puntos" máximo 40 palabras.
10. Si el mensaje no trae un JSON de resultados válido sobre lluvia/sequía/humedad del suelo o pide algo fuera de este tema (por ejemplo conversación general o recomendaciones de cultivos), pon "titular": "Sin datos para interpretar", explica en "resumen" qué hace falta, incluye al menos un punto en "puntos" (por ejemplo con tema "donde") y una nota breve en "cuidado"."""

ESQUEMA = {
    "type": "object",
    "properties": {
        "titular": {"type": "string"},
        "resumen": {"type": "string"},
        "puntos": {"type": "array", "items": {"type": "object", "properties": {
            "tema": {"type": "string", "enum": list(TEMAS)}, "texto": {"type": "string"}},
            "required": ["tema", "texto"]}},
        "cuidado": {"type": "array", "items": {"type": "string"}},
        "para_pensar": {"type": "string"},
    },
    "required": ["titular", "resumen", "puntos", "cuidado"],
}

LIMITACIONES = {
    "es": [
        "Cada dato cubre unos 50 km: describe la zona en general, no una parcela ni un municipio exacto.",
        "La humedad del suelo viene de un modelo (MERRA-2), no de una medición directa.",
        "Estos datos muestran cambios, no sus causas.",
    ],
    "en": [
        "Each data point covers about 50 km: it describes the area in general, not a single plot or an exact municipality.",
        "Soil moisture comes from a model (MERRA-2), not from a direct measurement.",
        "These data show changes, not their causes.",
    ],
}
# Textos fijos de los resultados, por idioma
R = {
    "es": {"region": "Los Altos de Jalisco, México (20 municipios)", "fuente": "NASA POWER (modelo MERRA-2)",
           "capa": "zona de raíces", "prom": "mm al año (total de los 12 meses)", "c_lluvia": "mm por mes, por década",
           "c_humedad": "puntos de % de saturación, por década", "a": " a "},
    "en": {"region": "Los Altos de Jalisco, Mexico (20 municipalities)", "fuente": "NASA POWER (MERRA-2 model)",
           "capa": "root zone", "prom": "mm per year (sum of the 12 months)", "c_lluvia": "mm per month, per decade",
           "c_humedad": "percentage points of saturation, per decade", "a": " to "},
}


def _idioma(idioma: str | None, r: dict | None = None) -> str:
    idioma = idioma or (r or {}).get("idioma") or "en"
    if idioma not in R:
        raise ValueError("El idioma debe ser 'en' o 'es'.")
    return idioma


# --- Armar los resultados ---------------------------------------------------------------------
def _tendencia(serie: pd.Series, unidades: str, con_estacional: bool = False) -> dict | None:
    """Tendencia por década de las anomalías, con su veredicto; None si hay muy pocos datos.

    `unidades` va junto al número para que Gemini no confunda, por ejemplo, mm al año con mm por mes.
    El veredicto va como código fijo ("sube", "baja", "no concluyente", "sin tendencia") en los dos idiomas.
    """
    validos = serie.dropna()
    if validos.empty or validos.index.year.nunique() < MIN_ANIOS_TENDENCIA:
        return None
    try:
        anom = anomalias(serie)
        ols, mk = tendencia_ols(anom), mann_kendall(anom, metodo="hamed_rao")
    except ValueError:
        return None
    t = {
        "cambio_por_decada": round(ols["pendiente_decada"], 2),
        "unidades_del_cambio": unidades,
        "ic95": [round(ols["ic_bajo"], 2), round(ols["ic_alto"], 2)],
        "p_regresion": round(ols["p_valor"], 3),
        "p_mann_kendall": round(mk["p_valor"], 3),
        "veredicto": PALABRA[veredicto(ols, mk, "")["color"]],
        "anios_para_significancia": None,
    }
    faltan = anios_para_significancia(ols)
    if faltan is not None:
        t["anios_para_significancia"] = int(round(faltan))
    if con_estacional:
        est = mann_kendall(serie, metodo="estacional")
        t["p_mann_kendall_estacional"] = round(est["p_valor"], 3)
        t["tendencia_estacional"] = {"subida": "sube", "bajada": "baja"}.get(est["tendencia"], "sin tendencia")
    return t


def _resumen_seguro(funcion, serie, indice, periodo, idioma) -> dict | None:
    try:
        valores = funcion(serie)
        return resumen_indice(valores.loc[str(periodo[0]):str(periodo[1])], indice, idioma=idioma)
    except ValueError:
        return None


def resultados(zona: str, periodo: tuple[int, int], lluvia: pd.Series, humedad: pd.Series | None,
               capa: str | None = None, fuente: str | None = None,
               referencia: tuple[int, int] = REFERENCIA, idioma: str = "en") -> dict:
    """El JSON con lo ya calculado, que se le da a Gemini.

    `lluvia` en mm por mes y `humedad` en % de saturación, idealmente desde antes de la referencia
    (para el SPI y "lo normal"); las tendencias y conteos se calculan solo dentro de `periodo`.
    `idioma` ("en" o "es") define los textos; las claves del JSON y los veredictos no cambian.
    """
    idioma = _idioma(idioma)
    tx = R[idioma]
    a0, a1 = periodo
    en_periodo = slice(f"{a0}-01-01", f"{a1}-12-01")
    tot = acumulados(lluvia.loc[en_periodo])
    sequia = _resumen_seguro(lambda s: spi(s, 6, referencia), lluvia, "spi", periodo, idioma)
    estres = _resumen_seguro(lambda s: estres_hidrico(s, referencia), humedad, "estres", periodo, idioma) \
        if humedad is not None else None
    anual = tot["anual_mm"].dropna()
    return {
        "idioma": idioma,
        "region": tx["region"],
        "zona": zona,
        "periodo": f"{a0}-{a1}",
        "referencia_normal": f"{referencia[0]}-{referencia[1]}",
        "fuente": fuente or tx["fuente"],
        "lluvia": {
            "promedio_anual_mm": int(round(anual.mean())) if len(anual) else None,
            "unidades_del_promedio": tx["prom"],
            "tendencia": _tendencia(lluvia.loc[en_periodo], tx["c_lluvia"]),
        },
        "sequia_meteorologica": None if sequia is None else {
            "indice": "SPI-6",
            "meses_en_sequia": sequia["meses_en_deficit"],
            "meses_totales": sequia["meses_totales"],
            "peor_periodo": tx["a"].join(sequia["peor_periodo"]) if sequia["peor_periodo"] else None,
            "categoria_peor": sequia["categoria_peor"],
            "ultimo_mes": sequia["ultimo_mes"],
            "valor_ultimo": sequia["valor_ultimo"],
            "categoria_ultimo": sequia["categoria_ultimo"],
        },
        "humedad_suelo": None if humedad is None else {
            "capa": capa or tx["capa"],
            "tendencia": _tendencia(humedad.loc[en_periodo], tx["c_humedad"], con_estacional=True),
        },
        "estres_hidrico_suelo": None if estres is None else {
            "meses_en_deficit": estres["meses_en_deficit"],
            "meses_totales": estres["meses_totales"],
            "meses_en_deficit_ultimos_5_anios": estres["meses_en_deficit_ultimos"],
            "peor_periodo": tx["a"].join(estres["peor_periodo"]) if estres["peor_periodo"] else None,
        },
        "limitaciones": list(LIMITACIONES[idioma]),
    }


# --- Resumen con plantillas (siempre funciona) ------------------------------------------------
P = {   # plantillas por idioma
    "es": {
        "sin_datos": "No hay datos suficientes para medir la tendencia de {n}.",
        "clara": "{N} {v} con claridad: unos {c} {u} por década, y las dos pruebas lo confirman.",
        "verbos": {"sube": "sube", "baja": "baja"},
        "no_clara": "En {n} no se ve una tendencia clara: los cambios caben en la variación normal.",
        "pista": (" Pero al comparar cada mes con el mismo mes de otros años (prueba por temporada), sí {v}: "
                  "es una pista que conviene confirmar."),
        "faltan": " Con datos de unos {a} años más se podría saber con seguridad.",
        "lluvia": "la lluvia", "humedad": "la humedad del suelo", "humedad_capa": "la humedad del suelo ({c})",
        "u_lluvia": "mm por mes", "u_humedad": "puntos de % de saturación", "y": " y ",
        "baja_t": "{q} va{s} a la baja en {z}", "sin_cambios": "Sin cambios claros en el agua de {z}",
        "sequia": "Hubo sequía meteorológica (llovió menos de lo normal) en {m} de {t} meses.",
        "peor": " La peor fue de {p} ({c}).",
        "estres": ("El suelo estuvo más seco de lo normal (estrés hídrico del suelo) en {m} de {t} meses; "
                   "{u} de ellos en los últimos 5 años."),
        "resumen": "Entre {a0} y {a1}, en {z} de Los Altos de Jalisco, comparamos cada mes con lo normal de {r0} a {r1}. ",
        "senales": "Algunas señales apuntan a menos agua.", "sin_tend": "Por ahora no hay una tendencia clara.",
        "pensar": "¿Qué otros datos ayudarían a entender por qué cambia el agua en tu región?",
    },
    "en": {
        "sin_datos": "There are not enough data to measure the trend in {n}.",
        "clara": "{N} {v} clearly: about {c} {u} per decade, and both tests confirm it.",
        "verbos": {"sube": "rises", "baja": "falls"},
        "no_clara": "{N} shows no clear trend: the changes fit within normal variation.",
        "pista": (" But when each month is compared with the same month in other years (seasonal test), it {v}: "
                  "a clue worth confirming."),
        "faltan": " About {a} more years of data would tell us for sure.",
        "lluvia": "rainfall", "humedad": "soil moisture", "humedad_capa": "soil moisture ({c})",
        "u_lluvia": "mm per month", "u_humedad": "percentage points of saturation", "y": " and ",
        "baja_t": "{q} {s} going down in {z}", "sin_cambios": "No clear change in water in {z}",
        "sequia": "There was meteorological drought (less rain than normal) in {m} of {t} months.",
        "peor": " The worst was from {p} ({c}).",
        "estres": ("The soil was drier than normal (soil water stress) in {m} of {t} months; "
                   "{u} of them in the last 5 years."),
        "resumen": "From {a0} to {a1}, in {z} of Los Altos de Jalisco, we compared each month with the normal of {r0} to {r1}. ",
        "senales": "Some signs point to less water.", "sin_tend": "For now there is no clear trend.",
        "pensar": "What other data would help explain why water is changing in your region?",
    },
}


def _frase_tendencia(nombre: str, t: dict | None, unidades: str, idioma: str) -> str:
    p = P[idioma]
    mayus = nombre[0].upper() + nombre[1:]
    if t is None:
        return p["sin_datos"].format(n=nombre)
    if t["veredicto"] in ("sube", "baja"):
        return p["clara"].format(N=mayus, v=p["verbos"][t["veredicto"]], c=abs(t["cambio_por_decada"]), u=unidades)
    texto = p["no_clara"].format(n=nombre, N=mayus)
    if t.get("tendencia_estacional") in ("sube", "baja"):
        texto += p["pista"].format(v=p["verbos"][t["tendencia_estacional"]])
    if t.get("anios_para_significancia"):
        texto += p["faltan"].format(a=t["anios_para_significancia"])
    return texto


def _en(zona: str) -> str:
    """'Toda la región' / 'Whole region' a mitad de frase; los nombres propios se quedan igual."""
    if zona.lower().startswith("whole"):
        return "the whole" + zona[5:]
    if zona.lower().startswith("toda"):
        return "t" + zona[1:]
    return zona


def resumen_sin_ia(r: dict, idioma: str | None = None) -> dict:
    """Resumen con plantillas, con el mismo formato que Gemini. Solo usa cifras de `r`.

    Sin `idioma`, usa el de los resultados (y si no trae, inglés).
    """
    idioma = _idioma(idioma, r)
    p = P[idioma]
    ll, hu = r["lluvia"], r["humedad_suelo"]
    se, es = r["sequia_meteorologica"], r["estres_hidrico_suelo"]
    t_ll = ll["tendencia"] if ll else None
    t_hu = hu["tendencia"] if hu else None
    bajan = [p[n] for n, t in (("lluvia", t_ll), ("humedad", t_hu)) if t and t["veredicto"] == "baja"]
    zona = _en(r["zona"])
    if bajan:
        q = p["y"].join(bajan)
        varios = len(bajan) > 1
        s = ("n" if varios else "") if idioma == "es" else ("are" if varios else "is")
        titular = p["baja_t"].format(q=q, s=s, z=zona)
    else:
        titular = p["sin_cambios"].format(z=zona)

    puntos = [{"tema": "lluvia", "texto": _frase_tendencia(p["lluvia"], t_ll, p["u_lluvia"], idioma)}]
    if se:
        texto = p["sequia"].format(m=se["meses_en_sequia"], t=se["meses_totales"])
        if se["peor_periodo"]:
            texto += p["peor"].format(p=se["peor_periodo"], c=se["categoria_peor"].lower())
        puntos.append({"tema": "sequia", "texto": texto})
    if hu:
        puntos.append({"tema": "humedad", "texto": _frase_tendencia(p["humedad_capa"].format(c=hu["capa"]),
                                                                     t_hu, p["u_humedad"], idioma)})
    if es:
        puntos.append({"tema": "estres", "texto": p["estres"].format(
            m=es["meses_en_deficit"], t=es["meses_totales"], u=es["meses_en_deficit_ultimos_5_anios"])})

    a0, a1 = r["periodo"].split("-")
    r0, r1 = r["referencia_normal"].split("-")
    resumen = p["resumen"].format(a0=a0, a1=a1, z=zona, r0=r0, r1=r1) + (p["senales"] if bajan else p["sin_tend"])
    return {
        "titular": titular[0].upper() + titular[1:],
        "resumen": resumen,
        "puntos": puntos,
        "cuidado": list(r.get("limitaciones") or []),
        "para_pensar": p["pensar"],
    }


# --- Resumen con Gemini (opcional) ------------------------------------------------------------
def _numeros(texto: str) -> set[float]:
    return {float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", texto)}


def cifras_inventadas(salida: dict, r: dict) -> set[float]:
    """Números que aparecen en la salida pero no en los resultados (ni redondeados). Vacío = todo bien."""
    permitidos = set()
    for n in _numeros(json.dumps(r, ensure_ascii=False)):
        permitidos |= {n, round(n), round(n, 1), round(n, 2)}
    return {n for n in _numeros(json.dumps(salida, ensure_ascii=False)) if n not in permitidos}


def _es_valida(salida) -> bool:
    return (isinstance(salida, dict) and all(isinstance(salida.get(k), str) for k in ("titular", "resumen"))
            and isinstance(salida.get("puntos"), list) and isinstance(salida.get("cuidado"), list)
            and all(isinstance(p, dict) and p.get("tema") in TEMAS and isinstance(p.get("texto"), str)
                    for p in salida["puntos"]))


ULTIMO_ERROR = ""   # por qué falló la última llamada (sin la clave), para diagnosticar


def resumen_con_gemini(r: dict, clave: str | None = None, modelo: str = MODELO, idioma: str | None = None,
                       pregunta: str | None = None) -> dict | None:
    """Resumen de Gemini con el formato de `resumen_sin_ia`; None si no hay clave, falla o inventa cifras.

    `idioma` ("en" o "es"); sin él, el de los resultados (y si no trae, inglés). `pregunta` es una consulta opcional del usuario sobre los mismos datos.
    """
    global ULTIMO_ERROR
    idioma = _idioma(idioma, r)
    clave = clave or os.environ.get("GEMINI_API_KEY")
    if not clave:
        ULTIMO_ERROR = "sin clave"
        return None
    mensaje = json.dumps(r, ensure_ascii=False) + (f"\n\nConsulta del usuario: {pregunta}" if pregunta else "")
    cuerpo = {
        "system_instruction": {"parts": [{"text": INSTRUCCIONES + (IDIOMA_EN if idioma == "en" else "")}]},
        "contents": [{"role": "user", "parts": [{"text": mensaje}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": ESQUEMA,
                             "thinkingConfig": {"thinkingLevel": "LOW"}},   # ajustes probados en AI Studio
    }
    salida = None
    for _ in range(REINTENTOS + 1):
        try:
            resp = requests.post(URL_GEMINI.format(modelo=modelo), json=cuerpo, timeout=TIMEOUT_S,
                                 headers={"x-goog-api-key": clave})   # la clave va en el encabezado, no en la URL
            if resp.status_code == 400 and "thinkingConfig" in cuerpo["generationConfig"]:
                cuerpo["generationConfig"].pop("thinkingConfig")      # modelo que no acepta ese ajuste
                continue
            resp.raise_for_status()
            salida = json.loads(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
            break
        except requests.HTTPError as e:
            ULTIMO_ERROR = f"HTTP {e.response.status_code}"
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as e:
            ULTIMO_ERROR = type(e).__name__
    if salida is None:
        if modelo != RESPALDO:
            return resumen_con_gemini(r, clave, RESPALDO, idioma, pregunta)
        return None
    if not _es_valida(salida):
        ULTIMO_ERROR = "formato inválido"
        return None
    inventadas = cifras_inventadas(salida, r)
    if inventadas:
        ULTIMO_ERROR = f"cifras que no vienen en los resultados: {sorted(inventadas)}"
        return None
    ULTIMO_ERROR = ""
    return salida
