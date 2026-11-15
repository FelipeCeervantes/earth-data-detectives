"""Pruebas del globo 3D (src/globo.py), del fondo que responde (src/fondo.py) y de sus piezas de estilo."""

import json
import re

import pytest

from src import estilo, fondo, globo, region

TEXTOS = {"volver": "Back to Los Altos", "planeta": "See the whole planet", "explorar": "Tap to explore",
          "terminar": "Done exploring", "acercar": "Zoom in", "alejar": "Zoom out", "sin_3d": "No 3D here.",
          "cargando": "Loading the globe…", "creditos": "Earth image: NASA Visible Earth (Blue Marble)",
          "municipio": "Municipality:", "lugar": "Los Altos de Jalisco", "aria": "3D globe"}


def celdas(id_zona: str = "los-altos") -> list[dict]:
    return [{"lat": c["lat"], "lon": c["lon"], "color": "#5CC8FF" if i % 2 else "#FFB454", "segura": i % 3 == 0,
             "lineas": [f"Cell {c['lat']:.2f}, {c['lon']:.3f}", "-1.20 mm/month per decade", "Significant trend"]}
            for i, c in enumerate(region.celdas(id_zona))]


ESTACIONES = [{"lat": 21.5633, "lon": -102.4394, "lineas": ["Rain gauge AJOJUCAR (TEOCALTICHE)"]}]


def datos_de(pagina: str) -> dict:
    """El JSON que la página recibe (const D = {...}), ya leído como lo leería el navegador."""
    crudo = re.search(r"const D = (\{.*?\}), T = D\.textos", pagina, re.S).group(1)
    return json.loads(crudo)


def test_el_html_trae_los_datos_de_python():
    pagina = globo.html("los-altos", celdas(), ESTACIONES, TEXTOS)
    d = datos_de(pagina)
    assert len(d["celdas"]) == len(region.celdas("los-altos")) == 12
    assert d["celdas"][0]["lineas"][1] == "-1.20 mm/month per decade"
    assert {c["color"] for c in d["celdas"]} == {"#5CC8FF", "#FFB454"}
    assert any(c["segura"] for c in d["celdas"]) and not all(c["segura"] for c in d["celdas"])
    assert d["estaciones"][0]["lineas"] == ["Rain gauge AJOJUCAR (TEOCALTICHE)"]
    assert d["textos"]["volver"] == "Back to Los Altos" and d["textos"]["explorar"] == "Tap to explore"
    assert len(d["municipios"]) == 20 and len(d["zona"]) >= 1
    assert d["relieve"]["filas"] == len(d["relieve"]["alturas"])
    assert d["paso"] == {"lat": region.PASO_LAT, "lon": region.PASO_LON}
    assert "Loading the globe…" in pagina


def test_se_adapta_a_la_zona():
    norte = datos_de(globo.html("altos-norte", celdas("altos-norte"), [], TEXTOS))
    sur = datos_de(globo.html("altos-sur", celdas("altos-sur"), [], TEXTOS))
    assert {m["nombre"] for m in norte["municipios"]} == set(region.ZONAS["altos-norte"]["municipios"])
    assert {m["nombre"] for m in sur["municipios"]} == set(region.ZONAS["altos-sur"]["municipios"])
    assert norte["vista"]["lat"] > sur["vista"]["lat"]  # la cámara vuela a otro lugar
    assert len(norte["celdas"]) == len(region.celdas("altos-norte"))


def test_escapa_los_textos():
    malo = '</script><img src=x onerror="alert(1)">&<b>'
    feas = [{**celdas()[0], "lineas": [malo, " ", "ok"]}]
    pagina = globo.html("los-altos", feas, [{"lat": 21.0, "lon": -102.0, "lineas": [malo]}],
                        {**TEXTOS, "lugar": malo, "cargando": malo})
    assert pagina.count("</script>") == 1  # solo la que cierra el código de la página
    assert "<img" not in pagina and "onerror=\"alert" not in pagina and " " not in pagina
    d = datos_de(pagina)  # y aun así el navegador recibe el texto completo, para pintarlo con textContent
    assert d["celdas"][0]["lineas"][0] == malo and d["estaciones"][0]["lineas"] == [malo]
    assert d["textos"]["lugar"] == malo
    assert "textContent" in pagina and "innerHTML" not in pagina


def test_un_texto_no_puede_suplantar_los_contornos():
    pagina = globo.html("los-altos", celdas(), [], {**TEXTOS, "lugar": "__ZONA__", "aria": "__RELIEVE__"})
    d = datos_de(pagina)
    assert d["textos"]["lugar"] == "__ZONA__" and isinstance(d["zona"], list) and isinstance(d["relieve"], dict)


def test_rendimiento_y_accesibilidad():
    pagina = globo.html("los-altos", celdas(), ESTACIONES, TEXTOS)
    assert "globe.gl@2.41.4" in pagina and "globe.gl-2.41.4.min.js" in pagina  # versión fija, local y en CDN
    assert "Math.min(window.devicePixelRatio || 1, 1.5)" in pagina            # proporción de píxeles máxima
    assert "IntersectionObserver" in pagina and "pauseAnimation" in pagina      # no dibuja fuera de pantalla
    assert "document.hidden" in pagina and "prefers-reduced-motion" in pagina
    assert "sinGlobo" in pagina and "webgl" in pagina                           # aviso si no hay 3D
    assert "bloqueado" in pagina and "pointer: coarse" in pagina                # el celular no atrapa el dedo
    assert "showGraticules(true)" in pagina and "showAtmosphere(true)" in pagina
    assert estilo.AGUA in pagina and estilo.BORDE_ZONA in pagina
    assert "<img" not in pagina  # sin logos: los créditos van como texto
    assert len(pagina.encode("utf-8")) < 200_000


def test_nada_de_bloques():
    pagina = globo.html("los-altos", celdas(), ESTACIONES, TEXTOS)
    altitudes = [float(a) for a in re.findall(r"(?:polygonAltitude|pointAltitude|htmlAltitude)\(([\d.]+)\)", pagina)]
    altitudes += [float(a) for a in re.findall(r"trazo\([^;]*?, (0\.\d+), ", pagina)]
    assert len(altitudes) >= 8 and max(altitudes) <= 0.01  # la tarea pide 0.01 como máximo
    assert "polygonSideColor" in pagina and "extruded" not in pagina


def test_sin_celdas_avisa():
    with pytest.raises(ValueError):
        globo.html("los-altos", [], [], TEXTOS)
    with pytest.raises(ValueError):
        globo.html("no-existe", celdas(), [], TEXTOS)


def test_simplificar_quita_puntos_sin_mover_los_extremos():
    linea = [[0.0, 0.0], [1.0, 0.0001], [2.0, -0.0001], [3.0, 0.0], [3.0, 1.0], [3.0, 2.0]]
    corta = globo.simplificar(linea, 0.004)
    assert corta == [[0.0, 0.0], [3.0, 0.0], [3.0, 2.0]]
    assert globo.simplificar(linea[:2]) == linea[:2]


def test_los_contornos_pesan_poco():
    d = datos_de(globo.html("los-altos", celdas(), [], TEXTOS))
    puntos = sum(len(a) for m in d["municipios"] for a in m["anillos"])
    assert 200 < puntos < 4000
    assert all(a[0] == a[-1] for m in d["municipios"] for a in m["anillos"])  # anillos cerrados


def test_encuadre_cubre_las_celdas():
    v = globo.encuadre([{"lat": 21.0, "lon": -102.5}, {"lat": 21.5, "lon": -101.875}])
    assert v == {"lat": 21.25, "lng": -102.1875, "dlat": 1.0, "dlon": 1.25}


def test_el_fondo_responde_y_tiene_lluvia_con_profundidad():
    pagina = fondo.html()
    assert "mousemove" in pagina and "scroll" in pagina          # parallax
    assert "dd-lluvia--mas" in pagina and "salpica" in pagina    # más gotas si llovió más; salpicaduras
    assert "prefers-reduced-motion" in pagina and "Math.min(devicePixelRatio, 1.5)" in pagina
    assert "document.hidden" in pagina


def test_escala_de_sequia_y_su_leyenda():
    assert estilo.color_sequia(10, 10, 50) == estilo.SEQUIA_BAJA
    assert estilo.color_sequia(50, 10, 50) == estilo.SEQUIA_ALTA
    assert estilo.color_sequia(30, 10, 50) not in (estilo.SEQUIA_BAJA, estilo.SEQUIA_ALTA)
    assert estilo.color_sequia(7, 7, 7).startswith("#")  # todas iguales: no divide entre cero
    leyenda = estilo.leyenda_sequia_html(31, 48, "en")
    assert "fewer months in drought (31)" in leyenda and "more months in drought (48)" in leyenda
    assert "menos meses en sequía (31)" in estilo.leyenda_sequia_html(31, 48, "es")


def test_estilo_del_globo_y_tarjetas_que_responden():
    assert ".st-key-globo" in estilo.CSS and f"height: {globo.ALTO_CELULAR}px" in estilo.CSS
    assert globo.ALTO == 760 and globo.ALTO_CELULAR == 420 and "82vh" in estilo.CSS  # grande en escritorio
    assert "translateY(-3px)" in estilo.CSS and "(hover: hover)" in estilo.CSS


def test_buscador_y_panel_de_cada_municipio_sin_aviso_demo():
    from src import globo
    celdas = [{"lat": 21.0, "lon": -102.5, "color": "#5CC8FF", "segura": True,
               "lineas": ["Cell 21.00, -102.500", "+1.20 mm/month per decade", "Significant"]}]
    pagina = globo.html("altos-sur", celdas, [], {"buscar": "Find <x>", "datos": "Data loaded",
                                                  "info": "The cell over its centre:", "cerrar": "Show zone"}, "en")
    assert 'id="buscador"' in pagina and 'list="lista"' in pagina and "DEMO" not in pagina and 'id="demo"' not in pagina
    escapado = "Find " + chr(92) + "u003cx" + chr(92) + "u003e"  # el texto viaja escapado
    assert escapado in pagina and "Find <x>" not in pagina
    assert '"lineas":["The cell over its centre:","+1.20 mm/month per decade","Significant"]' in pagina
    assert "Tepatitl" in pagina and pagina.index('"Lagos de Moreno"') > pagina.index('"otros"')
