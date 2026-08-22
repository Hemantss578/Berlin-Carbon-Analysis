# Provenance: `bezirk_emissions.csv`

Real, borough-level (Bezirk) greenhouse-gas emissions figures for Berlin, BISKO
methodology ("Bilanzierungs-Systematik Kommunal" — the standard German
municipal accounting framework: territorial-principle, all sectors in CO2
equivalents, upstream emissions included, national electricity mix used).

## Why only 2 of 12 boroughs have a number

Berlin does **not** publish a complete, uniform, borough-level CO2 dataset.
Checked directly against an official source: a Berlin House of Representatives
written question response, "Klimaschutz in den Bezirken"
(https://pardok.parlament-berlin.de/starweb/adis/citat/VT/19/SchrAnfr/S19-12665.pdf),
confirms that as of that response, most boroughs "weder ermittelt noch
evaluiert" (have neither measured nor evaluated) their greenhouse-gas
emissions at borough level. Only Charlottenburg-Wilmersdorf and Pankow have
published their own BISKO balances (each district commissions and publishes
its own, independently — there is no central Bezirk-level dataset to pull
from). This is a genuine data-availability gap in what Berlin publishes, not
a limitation of this project's data pipeline.

## Sources for the two populated rows

- **Charlottenburg-Wilmersdorf** — 1,777,611 t CO2-eq, 2023.
  https://www.berlin.de/ba-charlottenburg-wilmersdorf/verwaltung/aemter/umwelt-und-naturschutz/klimaschutz/artikel.712319.php
  (page also shows the district's year-by-year series back to 2016; note
  2022 onward uses a different traffic-emissions methodology — Google Maps
  mobility data — that the district's own page says isn't directly
  comparable to pre-2022 figures.)
- **Pankow** — ~1.45 million t CO2-eq, 2021 (most recent year with a
  published figure at the time of writing; 2022 data noted as provisional).
  https://www.berlin.de/ba-pankow/politik-und-verwaltung/beauftragte/klimaschutz/artikel.1507694.php

## Important caveats if you use this file

1. **Different years.** 2023 vs. 2021 — these are not directly comparable to
   each other, and both are stale relative to "now." Berlin's official
   citywide energy/CO2 balance is also published with a ~2 year lag (noted in
   Berlin's own climate-monitoring literature).
2. **Not a citywide total.** Do not sum this column and present it as
   "Berlin's total emissions" — 10 of 12 boroughs have no figure, so a sum
   would silently represent ~1/6th of the city's area as if it were the
   whole city.
3. **Not comparable district-to-district as a ranking signal**, given the
   year mismatch and each district's own reporting choices.

## Sourcing method

Fetched via web search + page fetch on 2026-08-22 (this session's date), not
via a bulk download — no consolidated file exists to download. If you find a
better source with more boroughs covered, replace this file (schema:
`bezirk,total_co2_tons,year,source_url,note`) and the loader in
`load_real_data.py` (`try_load_real_bezirk_emissions`) will pick it up as-is.
