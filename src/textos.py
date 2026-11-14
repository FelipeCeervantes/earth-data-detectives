"""Textos de la interfaz. Los del veredicto viven en src/analisis.py."""

# --- Recuadros "¿Qué significa?" de cada pestaña (fase Los Altos) -----------------------------
QUE_SIGNIFICA = {
    "resumen": (
        "Aquí está lo más importante en pocas palabras. Comparamos cada mes con lo normal de 1991 a 2020 "
        "y medimos si la lluvia y la humedad del suelo suben, bajan o se mantienen. Cada tarjeta tiene su "
        "pestaña, con las gráficas y los detalles."
    ),
    "lluvia": (
        "La lluvia se mide en milímetros: 1 mm es 1 litro de agua sobre cada metro cuadrado. En Los Altos casi "
        "toda cae entre junio y octubre, la temporada de lluvias que llena presas y bordos y moja el maíz de "
        "temporal. La tendencia dice si, año con año, llueve más o menos, después de quitar el ciclo de las "
        "estaciones."
    ),
    "sequia": (
        "Hay sequía meteorológica cuando llueve menos de lo normal para esa época del año. La medimos con el "
        "SPI (Índice de Precipitación Estandarizado): 0 es lo normal, -1 o menos es sequía y entre más negativo, "
        "más fuerte. El SPI-3 mira los últimos 3 meses (sequías cortas) y el SPI-6, los últimos 6 (sequías "
        "largas, que se notan en presas y pastos)."
    ),
    "humedad": (
        "La humedad del suelo dice qué tan mojada está la tierra, en porcentaje de saturación: 0 % es tierra "
        "completamente seca y 100 % es tierra con todos sus poros llenos de agua. La superficie cambia con cada "
        "lluvia; la zona de raíces es el agua que pueden usar los cultivos y los pastos; el perfil completo "
        "guarda la memoria de varios meses."
    ),
    "estres": (
        "Hay estrés hídrico del suelo cuando el suelo tiene menos agua de lo normal para ese mes. El número "
        "dice qué tan lejos está de lo de siempre, medido en \"variaciones normales\": 0 es lo normal y -1 o "
        "menos es déficit. Cada mes se compara con el mismo mes de otros años, así que un abril seco no se "
        "confunde con un agosto seco."
    ),
    "donde": (
        "El mapa muestra cómo cambia el agua en cada pedazo de la región. Cada cuadro es una celda de NASA "
        "POWER de unos 55 × 65 km: el color dice si ahí la tendencia va hacia más agua (azul) o hacia menos "
        "(óxido), y qué tan fuerte. Las líneas son los límites de los 20 municipios (INEGI)."
    ),
}

QUE_NO_ES = {
    "sequia": "Que llueva poco no significa que el suelo ya esté seco ni que los cultivos sufran: para eso "
              "revisa las pestañas de humedad y de estrés hídrico del suelo.",
    "estres": "No mide directamente el estrés de los cultivos: que el suelo tenga poca agua no prueba que el "
              "maíz o el agave estén sufriendo. Para eso se necesitan datos de campo o de vegetación.",
}

# Fuentes y limitaciones visibles en cada pestaña.
FUENTE_POWER = ("NASA POWER, a partir del modelo MERRA-2 (NASA GMAO), datos mensuales desde 1981. "
                "Lo normal = 1991–2020 (norma de la OMM).")
LIMITES = {
    "resumen": "Estos datos muestran cambios, no sus causas. Cada dato cubre unos 50 km: describe la zona en "
               "general, no una parcela ni un municipio exacto.",
    "lluvia": "La lluvia de MERRA-2 es una estimación de un modelo corregida con observaciones, no la de un "
              "pluviómetro. Cada dato cubre unos 50 km.",
    "sequia": "El SPI solo mira la lluvia: no ve el calor, el riego ni el agua del suelo.",
    "humedad": "La humedad del suelo viene de un modelo (MERRA-2), no de una medición directa en el campo.",
    "estres": "Viene de la humedad del suelo del modelo, no de los cultivos. Un mes en déficit no quiere decir "
              "que se perdió una cosecha.",
    "donde": "Cada celda promedia unos 55 × 65 km: no distingue una parcela de otra. Las celdas de las orillas "
             "también cubren parte de municipios vecinos.",
}
