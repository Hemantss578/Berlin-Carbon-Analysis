Real data files this project reads directly (no synthetic fallback — see
METHODOLOGY.md for the full picture):

- `trees_raw.csv` — a real Berlin tree cadastre export. Optional here IF a
  `*aumkataster*.csv` already exists under `data/raw/` (auto-discovered).
  See load_real_data.py and METHODOLOGY.md for expected columns.
- `plz_einwohner.csv` — **required**. Real nationwide German PLZ/population
  lookup (columns: plz, einwohner, qkm, lat, lon). This is the input the
  planting-priority ranking is built on (trees per real resident). Without
  it, `ml_engine.py` raises an error rather than fabricating population
  numbers.
- `bezirk_emissions.csv` — real (partial) Bezirk-level CO2 data, pre-filled
  with the 2 boroughs Berlin has actually published a figure for (see
  `BEZIRK_EMISSIONS_PROVENANCE.md` in this folder). The other 10 rows are
  intentionally empty — Berlin hasn't published those, so nothing fills the
  gap with a guess.
- `emissions_by_plz.csv` — optional, real PLZ-level CO2 emissions IF you have
  or can derive one yourself (Berlin's official data is Bezirk-level, not
  PLZ-level — see METHODOLOGY.md). Not required; the app works from
  `bezirk_emissions.csv` instead.
