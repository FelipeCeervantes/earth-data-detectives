# Fuente del polígono de Los Altos

`los_altos.geojson` sale del Marco Geoestadístico oficial de INEGI. El polígono no está dibujado a mano.

| Dato | Valor |
|---|---|
| Producto | **Marco Geoestadístico, Encuesta Intercensal 2025 (14 Jalisco)**, INEGI |
| Edición | 2026 (cobertura temporal 2025-07-31 a 2025-11-14), el más reciente publicado al 14 nov 2026 |
| Archivo | `14_jalisco.zip` (129 MB), capa de municipios `conjunto_de_datos/14mun.shp` (125 municipios) |
| Descarga | <https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551196649/14_jalisco.zip> |
| Ficha | <https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=794551196649> |
| Fecha de descarga | 14 de noviembre de 2026 |
| Acceso | Público, a través de internet (INEGI). Se cita como: *INEGI. Marco Geoestadístico, Encuesta Intercensal 2025.* |

## Cómo se procesó (`scripts/preparar_region.py`)
1. Lee `14mun.shp` (texto en ISO-8859-1) en su proyección original: Lambert Conformal Conic, ITRF2008/GRS80 (EPSG:6372, metros).
2. Filtra los 20 municipios por su nombre oficial (`NOMGEO`). El script falla si falta alguno.
3. Convierte las coordenadas a longitud/latitud con la inversa exacta de Lambert (Snyder 15-9 a 15-11). ITRF2008 y WGS84 coinciden a menos de 1 m.
4. Une los municipios de cada zona y simplifica los contornos con una tolerancia de 0.0015° (unos 150 m). Las coordenadas se redondean a 5 decimales (1 m).
5. Guarda 23 rasgos (3 zonas y 20 municipios, cada municipio con su `cvegeo` y su `zona`): unos 125 KB.

Para regenerarlo: descarga el zip en `data/inegi/` (git lo ignora) y corre `pip install pyshp shapely` y `python scripts/preparar_region.py`. La app no necesita esas librerías: solo lee el GeoJSON.

## Municipios (CVEGEO)
**Altos Norte (8), unos 8,160 km²:** Encarnación de Díaz (14035), Lagos de Moreno (14053), Ojuelos de Jalisco (14064), San Diego de Alejandría (14072), San Juan de los Lagos (14073), Teocaltiche (14091), Unión de San Antonio (14109), Villa Hidalgo (14116).

**Altos Sur (12), unos 6,570 km²:** Acatic (14001), Arandas (14008), Cañadas de Obregón (14117), Jalostotitlán (14046), Jesús María (14048), Mexticacán (14060), San Ignacio Cerro Gordo (14125), San Julián (14074), San Miguel el Alto (14078), Tepatitlán de Morelos (14093), Valle de Guadalupe (14111), Yahualica de González Gallo (14118).

Las áreas son aproximadas: se calcularon en la proyección Lambert de INEGI, que es conforme y no conserva el área exacta.
Comprobado: las cabeceras de Tepatitlán y Arandas caen en Altos Sur, la de Lagos de Moreno en Altos Norte, y Guadalajara y Aguascalientes quedan fuera.
