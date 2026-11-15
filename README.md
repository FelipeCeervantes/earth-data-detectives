# Earth Data Detectives · Los Altos de Jalisco 🌎

A Python + Streamlit app for the NASA Space Apps Challenge 2026. It explains in plain language how **rainfall** and **soil moisture** have changed in the 20 municipalities of **Los Altos de Jalisco**, Mexico: whether there has been **meteorological drought** or **soil water stress**, how much things change, where, and whether the change is statistically significant. It uses NASA POWER data (MERRA-2) and ends with a plain-language summary by Gemini.

- 🌐 **Live app:** https://earth-data-detectives.streamlit.app
- 📄 **The solution on one page:** [docs/solucion.md](docs/solucion.md)
- 📝 **Project page texts (submission):** [docs/entrega/project-page.md](docs/entrega/project-page.md)

## Run it (Python 3.11 or newer)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
pytest -q                     # runs the test suite
streamlit run app.py
```

NASA POWER needs no account. The Gemini summary is optional: if the environment variable `GEMINI_API_KEY` exists (or a secret with that name on Streamlit Community Cloud), the app uses it; otherwise it shows a template-based summary. The key never goes in the code or the repository.

```
app.py              Streamlit interface
src/region.py       the 20 municipalities, zones and data grid cells (INEGI boundaries)
src/catalogo.py     variables: rainfall and soil moisture (name, definition, units, source)
src/datos.py        download, cache and offline backup of the series
src/analisis.py     trends and statistical tests
src/indices.py      meteorological drought (SPI), soil water stress and rainfall totals
src/contraste.py    checks against CONAGUA: rain gauges (SMN) and Mexico's Drought Monitor
src/explicar.py     plain-language summary (templates and Gemini)
src/estilo.py       visual identity ("sky over dry land")
src/textos.py       interface texts
data/region/        Los Altos boundaries (INEGI); data/ is otherwise a local cache
demos/              stored series so the app works offline, plus the CONAGUA checks
docs/               solution page, submission texts, brand guide, deployment guide and screenshots
tests/              tests (pytest)
```

License: MIT (see LICENSE). Built for the NASA Space Apps Challenge 2026.
