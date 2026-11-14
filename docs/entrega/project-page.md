# Earth Data Detectives: Los Altos de Jalisco

> Texts for the NASA Space Apps 2026 project page, ready to copy and paste. Every number comes from the app (NASA POWER, whole region, 2001–2024, normal = 1991–2020). Fields marked **[TO FILL]** are completed before submitting.

**Challenge:** [TO FILL: the challenge title in English, exactly as it appears on the Space Apps site]
**Team:** [TO FILL: team name and members, exactly as registered]

## Slogan (pick one)
1. Is Los Altos running out of water? Ask the data.
2. NASA data, plain words: rain and soil in Los Altos de Jalisco.
3. Every month is a clue. Every trend gets a verdict.

## High-level summary
Los Altos de Jalisco, a highland region of 20 municipalities in western Mexico, depends on rain and soil moisture for its farms, dairy cattle and families. People there often ask whether the region is drying out, but the satellite and model data that could answer it are hard to find, process and interpret. Earth Data Detectives is a web app that turns NASA data into plain-language answers. You choose a zone (the whole region, Altos Norte or Altos Sur) and a period, and the app compares every month with the 1991–2020 normal. It tells you whether rainfall and soil moisture are changing, how much per decade, and whether the change is statistically significant. It also measures meteorological drought (SPI) and soil water stress, shows where change is strongest on a map, and ends with a short summary written by AI that may only use numbers the app has already calculated. Our goal is to democratize scientific information: anyone, expert or not, should be able to understand what is happening with the water where they live.

## Project demo
- Demo: [TO FILL: link to the 7 slides (PDF) or the 30-second video]
- Live app: [TO FILL: link to the app on Streamlit Community Cloud]
- Source code: https://github.com/FelipeCeervantes/earth-data-detectives

## Project details

### What does it do?
- Covers only Los Altos de Jalisco: 20 municipalities, using official municipal boundaries from INEGI (Mexico's national statistics institute).
- Tracks two variables: **rainfall** and **soil moisture** in three layers (surface, root zone and full profile).
- Answers four questions for any zone and period: Is rainfall changing? Has there been **meteorological drought**? Is soil moisture changing? Has there been **soil water stress**? It also shows **where** change is strongest and **how sure** we can be.
- Every chart has a "What does it mean?" box, a "What it is not" note where needed, and its sources and limitations.
- Ends with a plain-language summary in English (or Spanish) by Gemini. If Gemini mentions a number that is not in the app's results, the app discards that answer and shows a template-based summary instead.
- Works offline: the 1981–2024 series are stored with the app.

### How does it work?
1. **Data:** monthly NASA POWER series (MERRA-2 model) for the 12 grid cells that cover the region, averaged by how much of each zone falls in each cell. Rainfall is converted to millimeters per month.
2. **Normal:** each month is compared with the same month in 1991–2020 (the World Meteorological Organization standard normal), which removes the seasonal cycle.
3. **Meteorological drought:** the Standardized Precipitation Index (SPI-3 and SPI-6, McKee et al., 1993). **Soil water stress:** the standardized anomaly of soil moisture for each month. It does not directly measure crop stress.
4. **Trends:** linear regression with a 95% confidence interval (autocorrelation-robust errors) and the Mann-Kendall test with Sen's slope, also in its seasonal form and with the Hamed-Rao correction. A trend is called "clear" only when both tests agree; otherwise the app says how many more years of data would be needed to be sure.
5. **Summary:** Python builds a structured summary of the results and Gemini explains it in plain words, under strict rules: no new numbers, no causes, no crop advice.

### What we found (2001–2024)
- **Rainfall:** about 652 mm per year in the whole region, with no clear trend yet: −3.04 mm per month per decade (95% CI −8.2 to 2.13). About 10 more years of data would tell us for sure.
- **Meteorological drought:** 36 of 288 months. The worst episode ran from January 2011 to January 2012 (extreme drought).
- **Soil moisture (root zone):** no clear overall trend, but the seasonal test, which compares each month with the same month in other years, detects a decline (p = 0.016).
- **Soil water stress:** 25 of 288 months, 10 of them in the last 5 years.
- **Where:** the signal is not the same everywhere. In Altos Sur the seasonal test detects declining soil moisture (p = 0.001), while in Altos Norte it does not (p = 0.051).
- These data show changes, not their causes.

### Benefits
- Students, farmers and local officials get evidence about their own region in plain language, without coding or statistics.
- Honest about uncertainty: "no clear trend" is presented as a valid result, together with how many more years of data would settle it.
- Guarded AI: the language model explains numbers but cannot invent them.

### What do we hope to achieve?
- Make NASA Earth data part of everyday conversations about water in Los Altos, in schools, in agricultural associations and in local government.
- Next steps: finer satellite products (GPM IMERG for rain and GLDAS for soil moisture), more regions of Mexico, early drought warnings for producers, and studying land-cover change (such as agave expansion) with validated data and without assuming causes.

### Tools, languages and software
Python 3.12, Streamlit, pandas, NumPy, SciPy, statsmodels, pymannkendall, Plotly, Folium (with OpenStreetMap), requests, pyshp and Shapely (only to prepare the region boundaries), pytest, Git and GitHub. AI: Gemini API (Google) inside the app; Claude Code (Anthropic) by the team.

## Use of artificial intelligence and NASA data
- **NASA data:** [NASA POWER](https://power.larc.nasa.gov/) monthly point data (community AG), parameters `PRECTOTCORR` (precipitation) and `GWETTOP`, `GWETROOT` and `GWETPROF` (surface, root-zone and profile soil wetness), 1981–2024. POWER is based on NASA's [MERRA-2](https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/) reanalysis. Each grid cell covers about 50 km, so results describe the region in general, not a single plot.
- **Gemini (Google):** writes the final plain-language summary inside the app. It receives only the structured results that Python calculated, follows rules that forbid new numbers, causes and crop advice, and its answer is checked automatically: if it contains any number that is not in the results, it is discarded.
- **Claude (Anthropic):** used by the team through Claude Code to write and test code, coordinate tasks and review each other's work. All statistics are computed by our tested Python code, not by AI.
- No NASA logos, flags or mission identifiers are used.

## References
**Data**
- NASA Prediction Of Worldwide Energy Resources (POWER) Project, NASA Langley Research Center. https://power.larc.nasa.gov/
- Gelaro, R., et al. (2017). The Modern-Era Retrospective Analysis for Research and Applications, Version 2 (MERRA-2). *Journal of Climate*, 30(14), 5419–5454.
- INEGI, Marco Geoestadístico (municipal boundaries of Jalisco). https://www.inegi.org.mx/temas/mg/
- Servicio Meteorológico Nacional (CONAGUA), Monitor de Sequía en México (for comparison). https://smn.conagua.gob.mx/es/climatologia/monitor-de-sequia/monitor-de-sequia-en-mexico
- Map tiles © OpenStreetMap contributors. https://www.openstreetmap.org/copyright

**Methods**
- McKee, T. B., Doesken, N. J., & Kleist, J. (1993). The relationship of drought frequency and duration to time scales. *8th Conference on Applied Climatology*, Anaheim, CA, 179–184.
- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13(3), 245–259.
- Kendall, M. G. (1975). *Rank Correlation Methods*. Charles Griffin.
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. *Journal of the American Statistical Association*, 63(324), 1379–1389.
- Hamed, K. H., & Rao, A. R. (1998). A modified Mann-Kendall trend test for autocorrelated data. *Journal of Hydrology*, 204(1–4), 182–196.
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703–708.
- Hussain, Md. M., & Mahmud, I. (2019). pyMannKendall: a python package for non parametric Mann Kendall family of trend tests. *Journal of Open Source Software*, 4(39), 1556.

**Software and AI**
- Python, Streamlit, pandas, NumPy, SciPy, statsmodels, pymannkendall, Plotly, Folium, requests, pyshp, Shapely, pytest (all open source).
- Gemini API, Google. https://ai.google.dev/
- Claude and Claude Code, Anthropic. https://www.anthropic.com/claude

## Limitations
- NASA POWER cells cover about 50 km: the app describes zones, not individual plots or exact municipal values.
- Soil moisture comes from a model (MERRA-2), not from field measurements, and the model uses rainfall as an input.
- SPI measures meteorological drought only; soil water stress here means drier-than-normal soil, not proven crop stress.
- The app shows changes and their statistical confidence, not their causes.
