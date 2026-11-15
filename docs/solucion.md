# TerraLens: the solution on one page


## 1. The problem
In **Los Altos de Jalisco**, a highland region of 20 municipalities in western Mexico, water sustains farms, dairy cattle and families, and many people ask **"are we running out of water?"**. NASA data can answer that, but it is hard to find, process and interpret without a science background. We want **anyone** to be able to see, with evidence and in plain words, how rainfall and soil moisture have changed in their region. **Democratizing scientific information.**

## 2. The solution
A web app (Python and Streamlit) that **interprets**, not just plots:
- It covers only the **20 municipalities of Los Altos** (Altos Norte and Altos Sur) and two variables: **rainfall** and **soil moisture** (surface, root zone and full profile).
- You choose the **zone** (whole region, Altos Norte or Altos Sur) and the **period** (2001–2024 by default).
- It answers four questions: Is rainfall changing? Has there been **meteorological drought**? Is soil moisture changing? Has there been **soil water stress**? It also shows **where** change is strongest and **how sure** we can be.
- Every chart has a **"What does it mean?"** box, and at the end a **plain-language summary** written by AI (Gemini) that may only explain numbers the app already calculated.

## 3. How it works
1. **Data:** monthly NASA POWER series for the 12 grid cells that cover the 20 municipalities (official INEGI boundaries), averaged by how much of each zone falls in each cell. Rainfall is converted to millimeters per month.
2. **Normal:** each month is compared with the same month in 1991–2020 (the World Meteorological Organization standard), which removes the seasons.
3. **Meteorological drought:** the SPI index (3 and 6 months) tells whether it rained less than normal for that time of year. **Soil water stress:** soil moisture compared with the normal for that month. It does not directly measure crop stress.
4. **Trends:** a regression with its margin of error and the Mann-Kendall test (also seasonal, and corrected because each month resembles the previous one) tell whether a change is real or could be chance. If it is not certain yet, the app says how many more years of data would be needed.
5. **Checks on the ground:** Is the NASA data right on the ground? The app checks it against two Mexican sources from CONAGUA: the monthly records of 20 rain gauges of the National Weather Service (SMN) and Mexico's Drought Monitor, which rates each municipality from D0 to D4.
6. **Summary:** Python builds the results and Gemini explains them. If Gemini mentions a number that is not in the results, or if there is no connection, the app uses a template-based summary.

**Findings (2001–2024, whole region):** about 652 mm of rain per year with no clear trend yet. The worst meteorological drought ran from January 2011 to January 2012 (extreme). Soil moisture shows no clear overall trend, but the seasonal test detects a decline, strongest in Altos Sur. POWER rainfall moves with the CONAGUA rain gauges year to year (correlation 0.96) and 71% of our drought months were also official drought. None of this tells us the cause.

## 4. NASA data
- **[NASA POWER](https://power.larc.nasa.gov/)** (monthly, 1981–2024, no account needed), based on NASA's **MERRA-2** model: rainfall (`PRECTOTCORR`) and soil moisture at the surface, root zone and full profile (`GWETTOP`, `GWETROOT`, `GWETPROF`). Each cell covers about 50 km, so it describes the zone in general, not a single plot.
- We also use the municipal boundaries of **INEGI's Marco Geoestadístico**, and we check POWER against **CONAGUA**: 20 SMN rain gauges and Mexico's **Drought Monitor**.

## 5. What's next
- **Working today:** trend analysis, SPI, soil water stress, the map, the summary with Gemini (or templates) and offline mode.
- **Future:** finer satellite data (GPM IMERG and GLDAS), more regions of Mexico, early drought warnings for producers, and studying crop changes with validated data.
