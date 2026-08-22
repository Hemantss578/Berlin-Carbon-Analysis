"""\

Data pipeline entry point for Berlin Smart Canopy — data/raw stage.
REAL DATA ONLY — no synthetic fallback.

- PLZ boundaries: real. Run build_real_plz_geojson.py first (see its
  docstring) to produce data/raw/berlin_plz.geojson from real Berlin postal
  code shapes. This script errors out if that file is missing rather than
  falling back to a fake grid.
- Tree inventory: real. See load_real_data.py — this script requires a real
  export at data/external/real/trees_raw.csv (or a *aumkataster*.csv under
  data/raw/, auto-discovered) and errors out with instructions if none is
  found, rather than generating synthetic trees.

Population and (partial, real) Bezirk-level emissions data are NOT staged
here — they're already-real files under data/external/real/ that
ml_engine.py reads directly via load_real_data.py; there's nothing to
"generate" for them.

See METHODOLOGY.md for where to obtain real tree data if you don't have it
yet — this sandbox's network policy blocks direct downloads from
daten.berlin.de and the Berlin geoportal, so that file needs to be supplied
manually.

Usage:
    python build_real_plz_geojson.py   # do this first
    python data_generator.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import geopandas as gpd

from load_real_data import try_load_real_trees, find_real_trees_csv, REAL_TREES_CSV


@dataclass(frozen=True)
class Paths:
    project_root: Path = Path(__file__).resolve().parent
    data_raw: Path = project_root / "data" / "raw"

    trees_csv: Path = data_raw / "baumbestand_berlin.csv"
    plz_geojson: Path = data_raw / "berlin_plz.geojson"


def _ensure_dirs(paths: Paths) -> None:
    paths.data_raw.mkdir(parents=True, exist_ok=True)


def main() -> None:
    paths = Paths()
    _ensure_dirs(paths)

    if not paths.plz_geojson.exists():
        raise FileNotFoundError(
            f"{paths.plz_geojson} not found. Run `python build_real_plz_geojson.py` first — "
            "this project uses real Berlin PLZ boundaries only; there is no synthetic fallback."
        )

    plz_gdf = gpd.read_file(paths.plz_geojson)
    plz_gdf["PLZ"] = plz_gdf["PLZ"].astype(str)
    if plz_gdf.crs is None:
        plz_gdf = plz_gdf.set_crs("EPSG:4326")
    else:
        plz_gdf = plz_gdf.to_crs("EPSG:4326")

    current_year = int(pd.Timestamp.today().year)

    if find_real_trees_csv() is None:
        raise FileNotFoundError(
            f"No real tree data found. This project uses real Berlin tree-cadastre data only "
            f"(no synthetic fallback). Place a real export at {REAL_TREES_CSV} (or a "
            "*aumkataster*.csv under data/raw/, auto-discovered) — see METHODOLOGY.md for "
            "where to get one — then re-run this script."
        )

    trees_df = try_load_real_trees(plz_gdf, current_year=current_year)
    if trees_df is None or trees_df.empty:
        raise RuntimeError(
            "A real tree file was found but produced zero usable rows after cleaning and the "
            "spatial join to PLZ polygons — check the source file's columns and coordinates."
        )

    # Re-write, normalized to EPSG:4326 (idempotent if already normalized).
    plz_gdf.to_file(paths.plz_geojson, driver="GeoJSON")
    trees_df.to_csv(paths.trees_csv, index=False)

    print("Berlin Smart Canopy raw datasets written (real data only):")
    print(f"- {paths.plz_geojson}  (PLZ boundaries: REAL, {len(plz_gdf):,} areas)")
    print(f"- {paths.trees_csv}  (trees: REAL, {len(trees_df):,} rows)")


if __name__ == "__main__":
    main()
