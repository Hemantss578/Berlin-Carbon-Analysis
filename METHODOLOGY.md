# Methodology & data sources

This document covers where the app's data comes from, how the two rankings (planting priority
and species carbon performance) are actually computed, and what's still an estimate rather than a
measurement. The short version: every input is real Berlin/German open data; the two formulas that
turn those inputs into a "kg CO2 per tree" number are proxy allometric equations, not a
field-validated model — treat absolute numbers as illustrative and relative comparisons (which
areas, which species) as the trustworthy part.

## Data sources

| Input | Status | Source |
|---|---|---|
| PLZ (postal code) boundaries | Real, 193 areas | [`berlin-postal-code-areas`](https://github.com/derhuerst/berlin-postal-code-areas) (ISC license), reprojected to EPSG:4326. Community-maintained, not an official geoportal export — spot-check before using for anything policy-relevant. See `data/external/berlin_plz_source/PROVENANCE.md`. |
| Trees | Real, 691,580 records | Berlin's tree cadastre (Baumkataster), exported to CSV and placed at `data/raw/`. Columns: species, planting year, trunk diameter, coordinates. |
| Population | Real | Nationwide German PLZ/population lookup at `data/external/real/plz_einwohner.csv` (columns: plz, einwohner, qkm, lat, lon). All 193 Berlin PLZ areas matched. Origin/license not independently confirmed — verify before any public or commercial use. |
| Borough (Bezirk) CO2 emissions | Real, 2 of 12 boroughs | Berlin doesn't publish a complete borough-level emissions dataset. Confirmed via an official [Berlin parliament written response](https://pardok.parlament-berlin.de/starweb/adis/citat/VT/19/SchrAnfr/S19-12665.pdf): most boroughs have neither measured nor published one. Charlottenburg-Wilmersdorf ([source](https://www.berlin.de/ba-charlottenburg-wilmersdorf/verwaltung/aemter/umwelt-und-naturschutz/klimaschutz/artikel.712319.php)) and Pankow ([source](https://www.berlin.de/ba-pankow/politik-und-verwaltung/beauftragte/klimaschutz/artikel.1507694.php)) are the two that have published a BISKO figure. Full sourcing and caveats in `data/external/real/BEZIRK_EMISSIONS_PROVENANCE.md`. |

Nothing in this table has a synthetic fallback. If a required file is missing, the pipeline scripts
(`data_generator.py`, `ml_engine.py`) raise an error with instructions rather than generating
placeholder data.

## Planting-priority ranking

Every PLZ area gets a priority score from two real inputs only: population density and trees per
1,000 residents.

```
priority_score = z(population_density) - z(trees_per_1000_residents)
```

More people and fewer trees per person both push an area's score (and rank) up. `ml_engine.py`
also fits a KMeans model on the same features to group areas into rough tiers, but the rank itself
is the simple z-score comparison above — inspectable without touching the model. PLZ areas without
a real population match are excluded from ranking entirely rather than filled in with a guess.

## Species carbon ranking

Each tree's estimated annual CO2 sequestration comes from a proxy allometric formula:

```
annual_kg = 0.045 * species_growth_factor * age_term(age) * trunk_diameter_cm ** 1.35
```

`age` and `trunk_diameter_cm` are real, per-tree measurements from the cadastre.
`species_growth_factor` used to be 16 hand-picked numbers with no citation. It's now derived from
a real source: the USDA Forest Service / EPA-published McPherson & Nowak method (*Method for
Calculating Carbon Sequestration by Trees in Urban and Suburban Settings*), which classifies tree
genera into Hardwood/Conifer x Slow/Moderate/Fast growth-rate classes, backed by a measured
age-vs-sequestration table. The factor for each class is that class's average annual increment
relative to Hardwood-Moderate (fixed at 1.0x):

| Class | Relative factor |
|---|---|
| Hardwood — Slow | 0.47x |
| Hardwood — Moderate | 1.00x |
| Hardwood — Fast | 1.77x |
| Conifer — Slow | 0.33x |
| Conifer — Moderate | 0.74x |
| Conifer — Fast | 1.37x |

And the genus-level classification used in this project (`SPECIES_GROWTH_FACTOR` in
`ml_engine.py`):

| Genus | Class | Basis |
|---|---|---|
| Quercus (oak) | Hardwood-Moderate | Most oaks in the source table are Moderate-to-Fast; Moderate chosen as the representative pick |
| Tilia (linden/lime) | Hardwood-Fast | Littleleaf linden, the common Berlin street lime, is Fast in the source table |
| Acer (maple) | Hardwood-Moderate | Norway/red maple — the common Berlin street maples — are Moderate |
| Platanus (plane/sycamore) | Hardwood-Fast | London plane is Fast |
| Betula (birch) | Hardwood-Moderate | Paper/white birch is Moderate |
| Fraxinus (ash) | Hardwood-Fast | Green/white ash is Fast |
| Robinia (black locust) | Hardwood-Fast | Fast in the source table |
| Aesculus (horsechestnut/buckeye) | Hardwood-Slow | Slow in the source table |
| Carpinus (hornbeam) | Hardwood-Slow | Not in the source table — general arboricultural consensus |
| Pinus (pine) | Conifer-Moderate | Scots pine — the common Berlin/Brandenburg pine — is "Scotch" in the source table, classed Moderate |
| Fagus (beech) | Hardwood-Slow | Slow in the source table |
| Corylus (hazel) | Hardwood-Moderate | Not in the source table (shrub-form genus) — conservative default |
| Prunus (cherry/plum) | Hardwood-Fast | Fast in the source table |
| Populus (poplar) | Hardwood-Fast | Fast in the source table, and well documented as one of the fastest-growing tree genera generally |
| Alnus (alder) | Hardwood-Fast | Fast in the source table |
| Other (unidentified) | Hardwood-Moderate | Generic default for mixed/unidentified cadastre entries |

Two caveats worth being explicit about: this is a genus-level classification, so it glosses over
real variation between species within a genus, and two genera (Carpinus, Corylus) aren't in the
source table at all, so they fall back to general consensus rather than a citation. The kg-per-tree
conversion itself is still a proxy formula, not a field-validated method like i-Tree Eco — treat
the resulting ranking as well-sourced and relative, not as an absolute carbon accounting.

## Why there's no predictive machine-learning model

An earlier version of this project trained a Random Forest to predict each area's 2050 carbon
absorption. Its training labels were generated by applying the same growth formula above to itself
— there was no real outcome data behind it, so the model could only ever learn to re-derive a
closed-form function it was already shown the inputs to. The R² looked good because the task was
circular, not because the model had learned anything about real urban forestry.

It's been replaced with `ml_engine.project_planting_scenario_tons()`: the same formula, called
directly. Same math, no model file, no training set, no hidden randomness. The tab that exposes
this in the app is called the Planting Calculator rather than a predictor, because that's what it
actually is — a calculation, not a forecast.

## Known limitations

- Borough-level CO2 data covers 2 of 12 boroughs, from different years (2021 and 2023) — not
  summable into a citywide total and not comparable district-to-district as a ranking signal.
- The sequestration formula (both per-tree and per-species) is an illustrative proxy, not a
  field-validated model. Absolute tonnage figures shouldn't be treated as measurements.
- The species growth-rate classification is genus-level, sourced from a U.S. Forest Service table
  that doesn't cover every genus in Berlin's cadastre (see the two "not in the source table" rows
  above).
- `plz_einwohner.csv`'s exact origin and license haven't been independently confirmed — verify
  before relying on it for anything beyond this project's own exploratory use.
- There's no automated test suite yet. Given how much of this project is "does the pipeline
  produce sane numbers," even a handful of `pytest` tests on `enrich_trees`, `build_plz_features`,
  and the PLZ-to-Bezirk spatial join would catch regressions early.
- Paths are hardcoded relative to each script's own location. Fine for a project this size; would
  want a config file before pulling from a live data source or adding an API key.

## Possible future improvements

- Replace the proxy allometric formula with a field-validated one (i-Tree Eco, or a German
  urban-forestry carbon study) if trunk-diameter-based biomass equations for these species become
  available.
- If Berlin ever publishes borough-level emissions more completely, `try_load_real_bezirk_emissions()`
  in `load_real_data.py` will pick up a wider `bezirk_emissions.csv` as-is — no code change needed,
  just replace the file.
- A genuine supervised 2050 forecast would need real longitudinal outcome data (planted N trees,
  measured absorption Y years later) to train on, which doesn't currently exist for Berlin. Without
  that, a transparent calculator is the more honest option.
