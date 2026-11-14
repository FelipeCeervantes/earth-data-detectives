"""Textos de la interfaz, en inglés (lo que ven los jueces) y en español (para que el equipo revise).

Uso:  t("tab.lluvia", idioma)  o  t("caso.pregunta", idioma, lugar="Los Altos").
Los textos del veredicto viven en src/analisis.py; los de categorías de índices, en src/indices.py.
ponytail: "¿Qué significa?" son textos provisionales de integrante-1; se cambian por los de
manual/tareas/01 cuando lleguen a manual/entregas/.
"""

from __future__ import annotations

IDIOMAS = ("en", "es")
IDIOMA_INICIAL = "en"

MESES = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
           "noviembre", "diciembre"],
}
DIAS = {
    "en": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    "es": ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"],
}

TEXTOS: dict[str, dict[str, str]] = {
    "en": {
        # Página, marca y panel
        "pagina.titulo": "Earth Data Detectives · Los Altos",
        "marca.nombre": "Earth Data Detectives",
        "marca.lema": "Climate case files · NASA POWER · 1981–2024",
        "panel.titulo": "Detective's panel",
        "panel.donde": "1 · Where?",
        "panel.municipios": "{n} municipalities: {lista}.",
        "panel.periodo": "2 · Which period?",
        "panel.normal": "Normal: 1991–2020 · Rainy season: June to October.",
        "panel.idioma": "Language",
        # Encabezado del caso
        "caso.prefijo": "Case No.",
        "caso.numero": "{lugar} · Rainfall and soil moisture · {a0}–{a1}",
        "caso.pregunta": "What is happening to the water in {lugar}?",
        "caso.nota": "Choose the zone and the period in the detective's panel (on a phone, open it with » at the "
                     "top left).",
        "lugar.los-altos": "Los Altos",
        # Avisos y errores
        "error.periodo_corto": "Choose a period of at least {n} years: with fewer, a trend cannot be told apart "
                               "from normal variation.",
        "error.entrada": "Check the zone or the period: {e}",
        "error.descarga": "The NASA POWER data could not be downloaded and there is no saved copy. Please try again "
                          "in a moment. ({e})",
        "error.tendencia": "There is not enough data to calculate a trend: {e}",
        "error.spi": "The SPI cannot be calculated: {e}",
        "error.capa": "The soil moisture of that layer could not be loaded. ({e})",
        "error.estres": "Soil water stress cannot be calculated: {e}",
        "error.celdas": "The data for each cell could not be loaded. ({e})",
        "aviso.sin_conexion": "No connection to NASA POWER: using the data saved in the app (1981–2024).",
        "spinner.descarga": "Loading rainfall and soil moisture from NASA POWER…",
        "spinner.resultados": "Calculating the results…",
        "spinner.celdas": "Calculating the trend of each cell…",
        # Pestañas
        "tab.resumen": "Summary", "tab.lluvia": "Rainfall", "tab.sequia": "Meteorological drought",
        "tab.humedad": "Soil moisture", "tab.estres": "Soil water stress", "tab.donde": "Where?",
        # Etiquetas de las piezas
        "etq.que_significa": "What does it mean?",
        "etq.que_no_es": "What it is not:",
        "etq.fuente_limites": "Source and limitations",
        "etq.fuentes": "Case file sources",
        "etq.resumen": "Summary in plain words",
        "etq.cuidado": "Handle with care",
        "etq.para_pensar": "Food for thought:",
        "tema.lluvia": "Rainfall", "tema.sequia": "Drought", "tema.humedad": "Moisture", "tema.estres": "Stress",
        "tema.donde": "Where",
        "sello.veredicto": "Verdict",
        "faltan": "At this rate, about <strong>{n} more years</strong> of data would be needed to be sure.",
        # Evidencias de una tendencia
        "ev.etiqueta": "Evidence {i:02d} · {titulo}",
        "ev.cambio.titulo": "Change per decade",
        "ev.cambio.nota": "With 95% confidence, between {lo} and {hi}.",
        "ev.cambio.ayuda": "How much it rises (+) or falls (−) on average every 10 years. Another way to measure it "
                           "(Sen's slope): {sen} {u}.",
        "ev.total.titulo": "Over {n} years",
        "ev.total.nota": "What changed over the whole period, according to the trend.",
        "ev.total.ayuda": "It is not the difference between the first and the last month, which depends a lot on "
                          "the weather of those days.",
        "ev.recta.titulo": "Straight-line test",
        "ev.recta.nota": "p-value of the regression. Below 0.05: very unlikely to be chance.",
        "ev.recta.ayuda": "Test 1, a straight trend line. ",
        "ev.mk.titulo": "Mann-Kendall test",
        "ev.mk.nota": "p-value, corrected because each month resembles the one before.",
        "ev.mk.ayuda": "Test 2, counts how many times the data go up or down over time. ",
        "ayuda.p": "The p-value says how likely it would be to see a trend like this if there were actually none. "
                   "Below 0.05 = very unlikely to be chance.",
        # Gráfica de tendencia
        "graf.ver": "Show in the chart",
        "graf.reales": "Actual values", "graf.anomalias": "Anomalies",
        "graf.ver.ayuda": "Anomaly = difference from the average for that month. It removes the seasonal cycle so "
                          "the trend is easier to see.",
        "graf.valor_mensual": "Monthly value", "graf.anomalia_mensual": "Monthly anomaly",
        "graf.margen": "Trend range (95% CI)", "graf.tendencia": "Trend", "graf.anio": "Year",
        "graf.eje_valor": "Value ({u})", "graf.eje_anomalia": "Anomaly ({u})",
        "graf.anot_total": "{cambio} {u} over {n} years",
        "graf.nota_anomalia": "Anomaly = difference from the average for that month in {a0}–{a1}.",
        "descargar": "Download {nombre} (CSV)",
        "csv.fecha": "date", "csv.anomalia": "anomaly",
        # Evidencias de un índice
        "ind.meses.titulo": "Months in {palabra}",
        "ind.meses.nota": "Months with the index at −1 or below ({pct}).",
        "ind.ultimos.titulo": "Last 5 years",
        "ind.ultimos.valor": "{n} months in {palabra}",
        "ind.ultimos.nota": "From {desde} to {hasta}.",
        "ind.peor.titulo": "Worst period",
        "ind.peor.ninguno": "None",
        "ind.peor.sin": "There were no months in deficit.",
        "ind.peor.ayuda": "The most intense run of consecutive months at −1 or below.",
        "ind.ultimo.titulo": "Latest month",
        "palabra.sequia": "drought", "palabra.deficit": "deficit",
        "banda.moderado": "moderate", "banda.severo": "severe", "banda.extremo": "extreme",
        # Lluvia: acumulados
        "lluvia.acum.titulo": "Rainfall per year and in the rainy season (June to October)",
        "lluvia.acum.anual": "Yearly total", "lluvia.acum.temporada": "Rainy season (Jun–Oct)",
        "lluvia.acum.hover_anual": "%{x}: %{y:.0f} mm in the year",
        "lluvia.acum.hover_temp": "%{x}: %{y:.0f} mm from June to October",
        "lluvia.acum.normal": "Normal: {mm} mm per year (1991–2020)",
        "lluvia.acum.incompletos": "Years without a bar are missing a month ({lista}). They are not filled with zero.",
        # Sequía, humedad, estrés
        "sequia.indice": "Index", "sequia.formato": "SPI-{e} (last {e} months)",
        "humedad.capa": "Soil layer",
        "capa.humedad_superficie": "Surface (5 cm)", "capa.humedad_raices": "Root zone (1 m)",
        "capa.humedad_perfil": "Full profile",
        "estres.eje": "Standardized anomaly",
        # ¿Dónde?
        "donde.variable": "Map variable", "donde.lluvia": "Rainfall",
        "donde.celda": "Cell {lat}, {lon} · {peso} of the zone",
        "donde.por_decada": "{pend} {u} per decade · {icono} {palabra}",
        "donde.segura": "<b>Significant trend</b>: both tests agree",
        "donde.no_segura": "Trend not yet significant",
        "leyenda.menos": "less water", "leyenda.mas": "more water", "leyenda.por_decada": "per decade",
        "leyenda.segura": "Thick border: significant trend", "leyenda.no_segura": "Dashed border: not yet significant",
        "leyenda.cuenta": "{n} of {total} cells with a significant trend.",
        "tabla.ver": "Show the table of cells",
        "tabla.celda": "Cell", "tabla.zona": "% of the zone", "tabla.cambio": "Change per decade ({u})",
        "tabla.veredicto": "Verdict", "tabla.segura": "Significant trend?", "tabla.si": "Yes", "tabla.no": "Not yet",
        # Resumen
        "res.lluvia": "Rainfall", "res.sequia": "Meteorological drought (SPI-6)",
        "res.humedad": "Soil moisture (root zone)", "res.estres": "Soil water stress",
        "res.sin_datos": "Not enough data",
        "res.por_decada": "{v} {u} per decade.",
        "res.promedio": "On average, {mm} mm per year.",
        "res.meses": "{n} of {total} months",
        "res.peor": "Worst: {periodo} ({cat}).",
        "res.sin_rachas": "No drought spells.",
        "res.ultimos": "{n} of them in the last 5 years.",
        "res.u_lluvia": "mm/month", "res.u_humedad": "% points",
        "res.capa": "root zone",
        "res.origen_ia": "Written by Gemini from the results the app calculated (checked: it adds no new numbers).",
        "res.origen_plantillas": "Written with templates from the results the app calculated.",
        # Fuentes
        "creditos": (
            '<a href="https://power.larc.nasa.gov/">NASA POWER</a> (NASA Langley Research Center), with data from the '
            '<a href="https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/">MERRA-2</a> model (NASA GMAO): rainfall and soil '
            'moisture. Municipal boundaries: <a href="https://www.inegi.org.mx/temas/mg/">INEGI Geostatistical '
            'Framework</a> (2025 Intercensal Survey). Drought: SPI (McKee et al., 1993). Made by the Earth Data '
            "Detectives team for the NASA Space Apps Challenge."
        ),
        "fuente_power": "NASA POWER, from the MERRA-2 model (NASA GMAO), monthly data since 1981. "
                        "Normal = 1991–2020 (WMO climate normal).",
        # ¿Qué significa?, qué no es y limitaciones
        "significa.resumen": (
            "Here is what matters most, in a few words. We compare each month with what was normal from 1991 to 2020 "
            "and measure whether rainfall and soil moisture are rising, falling or staying the same. Each card has "
            "its own tab, with the charts and the details."),
        "significa.lluvia": (
            "Rainfall is measured in millimetres: 1 mm is 1 litre of water on each square metre. In Los Altos almost "
            "all of it falls between June and October, the rainy season that fills dams and ponds and waters the "
            "rain-fed maize. The trend says whether, year after year, it rains more or less, once the seasonal cycle "
            "is removed."),
        "significa.sequia": (
            "There is a meteorological drought when it rains less than normal for that time of year. We measure it "
            "with the SPI (Standardized Precipitation Index): 0 is normal, −1 or less is drought, and the more "
            "negative, the stronger. SPI-3 looks at the last 3 months (short droughts) and SPI-6 at the last 6 (long "
            "droughts, the ones you notice in dams and pastures)."),
        "significa.humedad": (
            "Soil moisture says how wet the ground is, as a percentage of saturation: 0% is completely dry soil and "
            "100% is soil with all its pores full of water. The surface changes with every rain; the root zone is "
            "the water that crops and pastures can use; the full profile keeps the memory of several months."),
        "significa.estres": (
            "There is soil water stress when the soil holds less water than normal for that month. The number says "
            "how far it is from usual, measured in \"normal variations\": 0 is normal and −1 or less is a deficit. "
            "Each month is compared with the same month in other years, so a dry April is not confused with a dry "
            "August."),
        "significa.donde": (
            "The map shows how the water is changing in each piece of the region. Each square is a NASA POWER cell of "
            "about 55 × 65 km: the colour says whether the trend there is towards more water (blue) or less (rust), "
            "and how strong it is. The lines are the borders of the 20 municipalities (INEGI)."),
        "no_es.sequia": "Little rain does not mean the soil is already dry or that crops are suffering: for that, "
                        "check the soil moisture and soil water stress tabs.",
        "no_es.estres": "It does not directly measure crop stress: soil with little water does not prove that the "
                        "maize or the agave is suffering. That needs field or vegetation data.",
        "limites.resumen": "These data show changes, not their causes. Each data point covers about 50 km: it "
                           "describes the zone in general, not a single plot or an exact municipality.",
        "limites.lluvia": "MERRA-2 rainfall is a model estimate corrected with observations, not a rain-gauge "
                          "reading. Each data point covers about 50 km.",
        "limites.sequia": "The SPI only looks at rainfall: it does not see heat, irrigation or soil water.",
        "limites.humedad": "Soil moisture comes from a model (MERRA-2), not from a direct field measurement.",
        "limites.estres": "It comes from the model's soil moisture, not from the crops. A month in deficit does not "
                          "mean a harvest was lost.",
        "limites.donde": "Each cell averages about 55 × 65 km: it does not tell one plot from another. Cells on the "
                         "edges also cover part of neighbouring municipalities.",
    },
    "es": {
        "pagina.titulo": "Detectives de Datos de la Tierra · Los Altos",
        "marca.nombre": "Detectives de Datos de la Tierra",
        "marca.lema": "Expedientes del clima · NASA POWER · 1981–2024",
        "panel.titulo": "Panel del detective",
        "panel.donde": "1 · ¿Dónde?",
        "panel.municipios": "{n} municipios: {lista}.",
        "panel.periodo": "2 · ¿En qué periodo?",
        "panel.normal": "Lo normal: 1991–2020 · Temporada de lluvias: junio a octubre.",
        "panel.idioma": "Idioma",
        "caso.prefijo": "Caso Nº",
        "caso.numero": "{lugar} · Lluvia y humedad del suelo · {a0}–{a1}",
        "caso.pregunta": "¿Qué está pasando con el agua en {lugar}?",
        "caso.nota": "Elige la zona y el periodo en el panel del detective (en el celular, ábrelo con » arriba a la "
                     "izquierda).",
        "lugar.los-altos": "Los Altos",
        "error.periodo_corto": "Elige un periodo de al menos {n} años: con menos, una tendencia no se puede "
                               "distinguir de la variación normal.",
        "error.entrada": "Revisa la zona o el periodo: {e}",
        "error.descarga": "No se pudieron descargar los datos de NASA POWER y no hay datos guardados. Intenta de "
                          "nuevo en un momento. ({e})",
        "error.tendencia": "No hay suficientes datos para calcular una tendencia: {e}",
        "error.spi": "No se puede calcular el SPI: {e}",
        "error.capa": "No se pudo cargar la humedad de esa capa. ({e})",
        "error.estres": "No se puede calcular el estrés hídrico del suelo: {e}",
        "error.celdas": "No se pudieron cargar los datos de cada celda. ({e})",
        "aviso.sin_conexion": "Sin conexión con NASA POWER: se usan los datos guardados en la app (1981–2024).",
        "spinner.descarga": "Cargando lluvia y humedad del suelo de NASA POWER…",
        "spinner.resultados": "Calculando los resultados…",
        "spinner.celdas": "Calculando la tendencia de cada celda…",
        "tab.resumen": "Resumen", "tab.lluvia": "Lluvia", "tab.sequia": "Sequía meteorológica",
        "tab.humedad": "Humedad del suelo", "tab.estres": "Estrés hídrico del suelo", "tab.donde": "¿Dónde?",
        "etq.que_significa": "¿Qué significa?",
        "etq.que_no_es": "Qué no es:",
        "etq.fuente_limites": "Fuente y limitaciones",
        "etq.fuentes": "Fuentes del expediente",
        "etq.resumen": "Resumen en palabras sencillas",
        "etq.cuidado": "Con cuidado",
        "etq.para_pensar": "Para pensar:",
        "tema.lluvia": "Lluvia", "tema.sequia": "Sequía", "tema.humedad": "Humedad", "tema.estres": "Estrés",
        "tema.donde": "Dónde",
        "sello.veredicto": "Veredicto",
        "faltan": "Con esta tendencia, harían falta unos <strong>{n} años</strong> más de datos para estar seguros.",
        "ev.etiqueta": "Evidencia {i:02d} · {titulo}",
        "ev.cambio.titulo": "Cambio por década",
        "ev.cambio.nota": "Con 95 % de confianza, entre {lo} y {hi}.",
        "ev.cambio.ayuda": "Cuánto sube (+) o baja (−) en promedio cada 10 años. Otra forma de medirlo (Sen): {sen} {u}.",
        "ev.total.titulo": "En {n} años",
        "ev.total.nota": "Lo que cambió en todo el periodo, según la tendencia.",
        "ev.total.ayuda": "No es la diferencia entre el primer y el último mes, que depende mucho del clima de esos días.",
        "ev.recta.titulo": "Prueba de la recta",
        "ev.recta.nota": "p-valor de la regresión. Menos de 0.05: muy poco probable que sea casualidad.",
        "ev.recta.ayuda": "Prueba 1, recta de tendencia. ",
        "ev.mk.titulo": "Prueba de Mann-Kendall",
        "ev.mk.nota": "p-valor, corregido porque cada mes se parece al anterior.",
        "ev.mk.ayuda": "Prueba 2, cuenta cuántas veces los datos suben o bajan con el tiempo. ",
        "ayuda.p": "El p-valor dice qué tan probable sería ver una tendencia así si en realidad no hubiera ninguna. "
                   "Menos de 0.05 = es muy poco probable que sea casualidad.",
        "graf.ver": "Ver en la gráfica",
        "graf.reales": "Valores reales", "graf.anomalias": "Anomalías",
        "graf.ver.ayuda": "Anomalía = diferencia con el promedio de ese mes. Quita el ciclo de las estaciones para que "
                          "se vea mejor la tendencia.",
        "graf.valor_mensual": "Valor mensual", "graf.anomalia_mensual": "Anomalía mensual",
        "graf.margen": "Margen de la tendencia (IC 95 %)", "graf.tendencia": "Tendencia", "graf.anio": "Año",
        "graf.eje_valor": "Valor ({u})", "graf.eje_anomalia": "Anomalía ({u})",
        "graf.anot_total": "{cambio} {u} en {n} años",
        "graf.nota_anomalia": "Anomalía = diferencia con el promedio de ese mes en {a0}–{a1}.",
        "descargar": "Descargar {nombre} (CSV)",
        "csv.fecha": "fecha", "csv.anomalia": "anomalia",
        "ind.meses.titulo": "Meses en {palabra}",
        "ind.meses.nota": "Meses con el índice en −1 o menos ({pct}).",
        "ind.ultimos.titulo": "Últimos 5 años",
        "ind.ultimos.valor": "{n} meses en {palabra}",
        "ind.ultimos.nota": "Desde {desde} hasta {hasta}.",
        "ind.peor.titulo": "Peor periodo",
        "ind.peor.ninguno": "Ninguno",
        "ind.peor.sin": "No hubo meses en déficit.",
        "ind.peor.ayuda": "La racha más intensa de meses seguidos en −1 o menos.",
        "ind.ultimo.titulo": "Último mes",
        "palabra.sequia": "sequía", "palabra.deficit": "déficit",
        "banda.moderado": "moderada", "banda.severo": "severa", "banda.extremo": "extrema",
        "lluvia.acum.titulo": "Lluvia de cada año y de la temporada de lluvias (junio a octubre)",
        "lluvia.acum.anual": "Total del año", "lluvia.acum.temporada": "Temporada (jun–oct)",
        "lluvia.acum.hover_anual": "%{x}: %{y:.0f} mm en el año",
        "lluvia.acum.hover_temp": "%{x}: %{y:.0f} mm de junio a octubre",
        "lluvia.acum.normal": "Lo normal: {mm} mm al año (1991–2020)",
        "lluvia.acum.incompletos": "Años sin barra: les falta algún mes ({lista}). No se rellenan con cero.",
        "sequia.indice": "Índice", "sequia.formato": "SPI-{e} (últimos {e} meses)",
        "humedad.capa": "Capa del suelo",
        "capa.humedad_superficie": "Superficie (5 cm)", "capa.humedad_raices": "Zona de raíces (1 m)",
        "capa.humedad_perfil": "Perfil completo",
        "estres.eje": "Anomalía estandarizada",
        "donde.variable": "Variable del mapa", "donde.lluvia": "Lluvia",
        "donde.celda": "Celda {lat}, {lon} · {peso} de la zona",
        "donde.por_decada": "{pend} {u} por década · {icono} {palabra}",
        "donde.segura": "<b>Tendencia segura</b>: las dos pruebas coinciden",
        "donde.no_segura": "Tendencia todavía no segura",
        "leyenda.menos": "menos agua", "leyenda.mas": "más agua", "leyenda.por_decada": "por década",
        "leyenda.segura": "Borde grueso: tendencia segura", "leyenda.no_segura": "Borde punteado: todavía no segura",
        "leyenda.cuenta": "{n} de {total} celdas con tendencia segura.",
        "tabla.ver": "Ver la tabla de las celdas",
        "tabla.celda": "Celda", "tabla.zona": "% de la zona", "tabla.cambio": "Cambio por década ({u})",
        "tabla.veredicto": "Veredicto", "tabla.segura": "¿Tendencia segura?", "tabla.si": "Sí", "tabla.no": "Todavía no",
        "res.lluvia": "Lluvia", "res.sequia": "Sequía meteorológica (SPI-6)",
        "res.humedad": "Humedad del suelo (raíces)", "res.estres": "Estrés hídrico del suelo",
        "res.sin_datos": "Sin datos suficientes",
        "res.por_decada": "{v} {u} por década.",
        "res.promedio": "En promedio, {mm} mm al año.",
        "res.meses": "{n} de {total} meses",
        "res.peor": "Peor: {periodo} ({cat}).",
        "res.sin_rachas": "Sin rachas de sequía.",
        "res.ultimos": "{n} de ellos en los últimos 5 años.",
        "res.u_lluvia": "mm/mes", "res.u_humedad": "puntos de %",
        "res.capa": "zona de raíces",
        "res.origen_ia": "Escrito por Gemini a partir de los resultados que calculó la app (revisado: no trae cifras "
                         "nuevas).",
        "res.origen_plantillas": "Escrito con plantillas a partir de los resultados que calculó la app.",
        "creditos": (
            '<a href="https://power.larc.nasa.gov/">NASA POWER</a> (NASA Langley Research Center), con datos del modelo '
            '<a href="https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/">MERRA-2</a> (NASA GMAO): lluvia y humedad del '
            'suelo. Límites municipales: <a href="https://www.inegi.org.mx/temas/mg/">Marco Geoestadístico de INEGI</a> '
            "(Encuesta Intercensal 2025). Sequía: SPI (McKee y colegas, 1993). Hecho por el equipo Detectives de Datos "
            "de la Tierra para el NASA Space Apps Challenge."
        ),
        "fuente_power": "NASA POWER, a partir del modelo MERRA-2 (NASA GMAO), datos mensuales desde 1981. "
                        "Lo normal = 1991–2020 (norma de la OMM).",
        "significa.resumen": (
            "Aquí está lo más importante en pocas palabras. Comparamos cada mes con lo normal de 1991 a 2020 y medimos "
            "si la lluvia y la humedad del suelo suben, bajan o se mantienen. Cada tarjeta tiene su pestaña, con las "
            "gráficas y los detalles."),
        "significa.lluvia": (
            "La lluvia se mide en milímetros: 1 mm es 1 litro de agua sobre cada metro cuadrado. En Los Altos casi "
            "toda cae entre junio y octubre, la temporada de lluvias que llena presas y bordos y moja el maíz de "
            "temporal. La tendencia dice si, año con año, llueve más o menos, después de quitar el ciclo de las "
            "estaciones."),
        "significa.sequia": (
            "Hay sequía meteorológica cuando llueve menos de lo normal para esa época del año. La medimos con el SPI "
            "(Índice de Precipitación Estandarizado): 0 es lo normal, −1 o menos es sequía y entre más negativo, más "
            "fuerte. El SPI-3 mira los últimos 3 meses (sequías cortas) y el SPI-6, los últimos 6 (sequías largas, "
            "que se notan en presas y pastos)."),
        "significa.humedad": (
            "La humedad del suelo dice qué tan mojada está la tierra, en porcentaje de saturación: 0 % es tierra "
            "completamente seca y 100 % es tierra con todos sus poros llenos de agua. La superficie cambia con cada "
            "lluvia; la zona de raíces es el agua que pueden usar los cultivos y los pastos; el perfil completo "
            "guarda la memoria de varios meses."),
        "significa.estres": (
            "Hay estrés hídrico del suelo cuando el suelo tiene menos agua de lo normal para ese mes. El número dice "
            "qué tan lejos está de lo de siempre, medido en \"variaciones normales\": 0 es lo normal y −1 o menos es "
            "déficit. Cada mes se compara con el mismo mes de otros años, así que un abril seco no se confunde con "
            "un agosto seco."),
        "significa.donde": (
            "El mapa muestra cómo cambia el agua en cada pedazo de la región. Cada cuadro es una celda de NASA POWER "
            "de unos 55 × 65 km: el color dice si ahí la tendencia va hacia más agua (azul) o hacia menos (óxido), y "
            "qué tan fuerte. Las líneas son los límites de los 20 municipios (INEGI)."),
        "no_es.sequia": "Que llueva poco no significa que el suelo ya esté seco ni que los cultivos sufran: para eso "
                        "revisa las pestañas de humedad y de estrés hídrico del suelo.",
        "no_es.estres": "No mide directamente el estrés de los cultivos: que el suelo tenga poca agua no prueba que "
                        "el maíz o el agave estén sufriendo. Para eso se necesitan datos de campo o de vegetación.",
        "limites.resumen": "Estos datos muestran cambios, no sus causas. Cada dato cubre unos 50 km: describe la zona "
                           "en general, no una parcela ni un municipio exacto.",
        "limites.lluvia": "La lluvia de MERRA-2 es una estimación de un modelo corregida con observaciones, no la de "
                          "un pluviómetro. Cada dato cubre unos 50 km.",
        "limites.sequia": "El SPI solo mira la lluvia: no ve el calor, el riego ni el agua del suelo.",
        "limites.humedad": "La humedad del suelo viene de un modelo (MERRA-2), no de una medición directa en el campo.",
        "limites.estres": "Viene de la humedad del suelo del modelo, no de los cultivos. Un mes en déficit no quiere "
                          "decir que se perdió una cosecha.",
        "limites.donde": "Cada celda promedia unos 55 × 65 km: no distingue una parcela de otra. Las celdas de las "
                         "orillas también cubren parte de municipios vecinos.",
    },
}


def t(clave: str, idioma: str = IDIOMA_INICIAL, **campos) -> str:
    """Texto de la interfaz en el idioma pedido (en/es), con sus campos ya puestos."""
    if idioma not in TEXTOS:
        raise ValueError(f"Idioma no válido: '{idioma}'. Usa 'en' o 'es'.")
    texto = TEXTOS[idioma][clave]
    return texto.format(**campos) if campos else texto


def tiene(clave: str, idioma: str = IDIOMA_INICIAL) -> bool:
    return clave in TEXTOS.get(idioma, {})


def mes_corto(mes: int, idioma: str) -> str:
    return MESES[idioma][mes - 1][:3]


def mes_largo(mes: int, anio: int, idioma: str) -> str:
    """'enero de 2020' / 'January 2020'."""
    return f"{MESES[idioma][mes - 1]} {anio}" if idioma == "en" else f"{MESES[idioma][mes - 1]} de {anio}"
