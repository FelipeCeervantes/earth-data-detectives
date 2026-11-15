"""Pruebas de la tarea 15: la página pesa menos, no recalcula lo que no cambió y el vidrio es más transparente."""

import base64
import json
import re
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

from src import estilo, fondo, globo

RAIZ = Path(__file__).parent.parent
APP = str(RAIZ / "app.py")


def test_relieve_compacto_conserva_las_alturas():
    original = json.loads(fondo.ARCHIVO_RELIEVE.read_text(encoding="utf-8"))
    r = fondo.relieve_compacto()
    crudo = base64.b64decode(r["alturas"])
    assert len(crudo) == r["filas"] * r["columnas"] == original["filas"] * original["columnas"]
    planas = [m for fila in original["alturas"] for m in fila]
    reconstruidas = [r["base"] + b * r["paso"] for b in crudo]
    assert max(abs(a - b) for a, b in zip(planas, reconstruidas)) <= r["paso"] / 2 + 0.1  # error menor a 5 m
    assert r["paso"] < 10 and r["contorno"] == original["contorno"]


def test_las_paginas_pesan_menos():
    assert len(fondo.html().encode("utf-8")) < 40_000  # antes: 71 KB
    assert "atob(" in fondo.html() and '"alturas":"' in fondo.html()
    assert len(globo._relieve()) < 20_000              # antes: 58 KB dentro del globo
    assert '"contorno"' not in globo._relieve()        # el globo ya trae los contornos de INEGI


def test_el_globo_se_reutiliza_si_no_cambia_nada():
    st.cache_data.clear()
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception

    def pagina():
        return next(e.proto.srcdoc for e in at.get("iframe") if "globe.gl" in e.proto.srcdoc)

    primera = pagina()
    assert len(primera.encode("utf-8")) < 110_000  # antes: 136 KB
    at.segmented_control(key="vista").set_value("lluvia").run()
    at.segmented_control(key="vista").set_value("resumen").run()
    assert pagina() == primera  # el mismo texto: el navegador no vuelve a cargar el iframe
    at.segmented_control(key="var_mapa").set_value("sequia").run()
    assert pagina() != primera and not at.exception


def test_cada_cache_tiene_tope_y_la_pagina_pinta_antes_de_lo_pesado():
    codigo = (RAIZ / "app.py").read_text(encoding="utf-8")
    decoradores = re.findall(r"@st\.cache_data\(([^)]*)\)", codigo)
    assert len(decoradores) >= 10
    assert all("CACHE" in d or "max_entries" in d for d in decoradores)  # la memoria no crece sin fin
    assert "max_entries=200" in codigo
    # el cielo y el fondo se mandan antes de importar scipy y statsmodels (src.analisis)
    assert codigo.index("st.html(E.CSS)") < codigo.index("from src.analisis import")
    for calculo in ("indices.acumulados(", "indices.spi(", "indices.estres_hidrico(", "contraste.monitor(",
                    "prediccion.proyectar(", "prediccion.probabilidad_sequia("):
        assert codigo.count(calculo) == 1 or calculo == "indices.spi(", calculo  # solo dentro de su caché


def test_websocket_comprimido_y_archivos_estaticos():
    config = (RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "enableWebsocketCompression = true" in config and "enableStaticServing = true" in config


def test_vidrio_mas_transparente_con_brillo_en_el_borde():
    relleno = float(re.search(r"rgba\(255,255,255,([\d.]+)\)", estilo.VIDRIO).group(1))
    assert 0.03 <= relleno <= 0.05  # antes 0.075
    css = estilo.CSS
    assert "--dd-vidrio-relleno" in css and "--dd-vidrio-filtro: blur(" in css and "--dd-vidrio-canto" in css
    assert "inset 0 1px 0 rgba(255,255,255,0.42)" in css          # luz fina en el canto de arriba
    assert "var(--dd-capsula)" in css and "--dd-capsula-elegida" in css  # botones: cápsulas de vidrio
    assert css.count("var(--dd-vidrio-canto)") >= 4                # tarjetas, menú, píldoras y botones (una regla) y globo
    assert "@supports not ((backdrop-filter: blur(1px))" in css and estilo.VIDRIO_SOLIDO in css  # respaldo sólido
    assert ".dd-limites" in css.split("background: var(--dd-vidrio-relleno) !important;")[0][-400:]
    cuerpo = css[len("<style>"):-len("</style>")]
    assert "<" not in cuerpo and ">" not in cuerpo  # st.html descarta la CSS si trae algo con forma de etiqueta


def test_el_globo_usa_el_mismo_vidrio():
    pagina = globo._HTML
    assert "brightness(.5)" in pagina and "rgba(9,34,66,.34)" in pagina  # menos relleno; el filtro oscurece lo de atrás
    assert "inset 0 1px 0 rgba(255,255,255,.3)" in pagina
    assert "@supports not ((backdrop-filter:blur(1px))" in pagina        # respaldo sólido


def test_gota_que_se_desliza_entre_botones():
    css = estilo.CSS
    assert "[data-gota]::before" in css and "--gota-l" in css and "dd-gota-a" in css
    assert "prefers-reduced-motion: reduce) { [data-gota]::before" in css      # sin animación si la piden
    assert "window.__ddGota" in estilo.GOTA_JS and "MutationObserver" in estilo.GOTA_JS
    assert "parent.document" in estilo.GOTA_HTML and "</script>" not in estilo.GOTA_JS
    cuerpo = css[len("<style>"):-len("</style>")]
    assert "<" not in cuerpo and ">" not in cuerpo


def test_sin_atenuado_y_cristal_opcional():
    assert '[data-stale="true"] { opacity: 1 !important' in estilo.CSS   # los paneles ya no se aclaran solos
    cristal = estilo.CSS_CRISTAL
    assert "url(#dd-cristal)" in cristal and "html[data-cristal-refracta]" in cristal
    cuerpo = cristal[len("<style>"):-len("</style>")]
    assert "<" not in cuerpo and ">" not in cuerpo
    assert 'id="dd-cristal"' in estilo.GOTA_JS and "feDisplacementMap" in estilo.GOTA_JS
    assert "</" not in estilo.GOTA_HTML.split("<script>", 1)[1].rsplit("</script>", 1)[0]   # el script no se corta


def test_boton_de_cristal_junto_al_idioma():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=120).run()
    assert not at.exception
    assert not any("dd-cristal" in h.proto.body for h in at.get("html"))
    at.toggle(key="cristal").set_value(True).run()
    assert any("url(#dd-cristal)" in h.proto.body for h in at.get("html"))

