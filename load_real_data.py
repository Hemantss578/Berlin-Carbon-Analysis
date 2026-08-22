"""\
Optional real-data loaders for trees and emissions.

This sandbox's network policy blocks direct downloads from daten.berlin.de and
the Berlin geoportal (FIS-Broker), so this project can't auto-fetch those two
files the way build_real_plz_geojson.py auto-fetches PLZ boundaries. Instead,
this module looks for files YOU place manually and normalizes them into the
schema the rest of the pipeline expects. If the files aren't present, both
functions return None and data_generator.py falls back to synthetic data (now
generated over the real PLZ geometry, at least).

Where to get real files — see METHODOLOGY.md for full detail and links:

  Trees   -> Berlin tree cadastre (Baumkataster / "Baumbestand Berlin"),
             via FIS-Broker (https://fbinter.stadt-berlin.de) or the Berlin
             Open Data portal. Export as CSV, and place it at:
                 data/external/real/trees_raw.csv
             Expected-ish columns (many aliases are recognized — see
             TREE_COLUMN_ALIASES below): species / genus, planting year,
             trunk diameter or circumference, and either lat/lon or
             EPSG:25833 x/y coordinates. This loader spatially joins each
             tree to the REAL PLZ polygon it physically falls inside —
             real cadastre exports come with Bezirk/Ortsteil/coordinates,
             not a ready-made PLZ column, so don't expect one.

  Emissions -> Berlin only publishes CO2 figures at Bezirk (borough) level
             or as point-source facility data (see METHODOLOGY.md) — there
             is no official PLZ-level CO2 dataset to drop in directly. If
             you've done your own Bezirk->PLZ allocation (or found a PLZ-
             level source), place the result at:
                 data/external/real/emissions_by_plz.csv
             with a PLZ column and a total CO2 (tons/year) column. This
             loader deliberately does NOT attempt automatic Bezirk->PLZ
             disaggregation — that's a methodology decision, not something
             to guess silently (see METHODOLOGY.md, "Emissions" section).

  Population -> data/external/real/plz_einwohner.csv (a nationwide German
             PLZ/population lookup, columns plz, einwohner, qkm, lat, lon;
             origin/license not independently confirmed, so verify before
             any public or commercial use). Required — this is the real
             signal the priority ranking is built on (trees per resident),
             replacing the old fabricated emissions+sealing formula.

  Bezirk emissions -> data/external/real/bezirk_emissions.csv. As of this
             writing Berlin does NOT publish a complete borough-level CO2
             dataset — confirmed via an official parliamentary written
             response, most boroughs have neither measured nor published
             one. Only 2 of 12 (Charlottenburg-Wilmersdorf, Pankow) have a
             real published figure, from different years. This file is
             pre-populated with those 2 real, sourced figures and NaN for
             the other 10 — see BEZIRK_EMISSIONS_PROVENANCE.md. The app
             shows these as real Bezirk-level data where available rather
             than fabricating PLZ-level numbers to fill the gap.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parent
REAL_DATA_DIR = PROJECT_ROOT / "data" / "external" / "real"

REAL_TREES_CSV = REAL_DATA_DIR / "trees_raw.csv"
REAL_EMISSIONS_CSV = REAL_DATA_DIR / "emissions_by_plz.csv"
REAL_POPULATION_CSV = REAL_DATA_DIR / "plz_einwohner.csv"
REAL_BEZIRK_EMISSIONS_CSV = REAL_DATA_DIR / "bezirk_emissions.csv"

# Fallback discovery: if trees_raw.csv isn't at the canonical path, look for a
# CSV matching this pattern directly under data/raw/ — real Baumkataster
# exports commonly land there first (with an auto-generated filename) before
# anyone remembers to move them. Avoids "just move the giant file" friction.
REAL_TREES_FALLBACK_GLOB = "*aumkataster*.csv"
REAL_TREES_FALLBACK_DIR = PROJECT_ROOT / "data" / "raw"


# ---------------------------------------------------------------------------
# Column-name aliasing — real exports rarely match our internal schema, and
# German cadastre exports commonly use German field names. We try a list of
# plausible aliases per canonical field rather than failing on the first
# mismatch. Exact match first; if nothing matches exactly, fall back to
# substring matching, since real exports often carry units in the header
# ("Stammumfang (cm)") that break an exact-match lookup.
# ---------------------------------------------------------------------------

def _first_matching_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    lower_map = {c.lower().strip(): c for c in df.columns}
    for alias in aliases:
        if alias.lower() in lower_map:
            return lower_map[alias.lower()]
    # Substring fallback (e.g. alias "stammumfang" matching header
    # "Stammumfang (cm)").
    for alias in aliases:
        for lower_col, orig_col in lower_map.items():
            if alias.lower() in lower_col:
                return orig_col
    return None


TREE_COLUMN_ALIASES = {
    # NOTE: "Kronendurchmesser"/crown diameter is NOT the same thing as trunk
    # diameter (an earlier version of this file conflated the two — crown
    # diameter is canopy width, unrelated to trunk girth). Real Berlin
    # cadastre exports typically only have trunk CIRCUMFERENCE
    # ("Stammumfang"), which try_load_real_trees converts to diameter via
    # /pi — see trunk_circumference_cm below.
    "species": ["species", "art", "art_dtsch", "art_deutsch", "gattung_deutsch", "gattung", "artname", "baumart"],
    "planting_year": ["planting_year", "pflanzjahr", "pflanzjahr_", "standalter_jahr", "baumjahr"],
    "trunk_diameter_cm": ["trunk_diameter_cm", "stammdurchmesser"],
    "trunk_circumference_cm": ["stammumfang", "stammumfg", "trunk_circumference_cm"],
    "latitude": ["latitude", "lat", "y_wgs84"],
    "longitude": ["longitude", "lon", "lng", "x_wgs84"],
    "x": ["x", "x_25833", "rechtswert", "easting"],
    "y": ["y", "y_25833", "hochwert", "northing"],
}

# Real cadastre exports use full German common names at species level (e.g.
# "Winter-Linde", "Sommer-Eiche, Stiel-Eiche") — Berlin's real Baumkataster
# alone has 765 distinct values. The rest of the pipeline (SPECIES_GROWTH_FACTOR
# in ml_engine.py, the planting-simulator sliders in app.py) works at GENUS
# level with a bounded set of buckets, so real species names are normalized
# down to genus here via substring keyword match. Coverage check against the
# real Baumkataster export: these 15 genera match ~89% of real trees by count;
# the rest fall into "Other" (a long tail of ~700 rarer species — willow, elm,
# whitebeam, hawthorn, honey locust, tree-of-heaven, etc.). Bucket names must
# stay in sync with ml_engine.SPECIES_GROWTH_FACTOR's keys.
REAL_SPECIES_KEYWORDS: dict[str, str] = {
    "linde": "Tilia (Linde)",
    "eiche": "Quercus (Eiche)",
    "ahorn": "Acer (Ahorn)",
    "platane": "Platanus",
    "birke": "Betula",
    "esche": "Fraxinus",
    "robinie": "Robinia (Robinie)",
    "kastanie": "Aesculus (Rosskastanie)",
    "hainbuche": "Carpinus (Hainbuche)",
    "kiefer": "Pinus (Kiefer)",
    "buche": "Fagus (Buche)",  # checked after "Hainbuche" so it doesn't shadow it
    "hasel": "Corylus (Hasel)",
    "kirsche": "Prunus (Kirsche)",
    "pappel": "Populus (Pappel)",
    "erle": "Alnus (Erle)",
}
SPECIES_OTHER_BUCKET = "Other"


def _normalize_species_to_genus(raw_species: pd.Series) -> pd.Series:
    lowered = raw_species.str.lower().fillna("")
    bucket = pd.Series(SPECIES_OTHER_BUCKET, index=raw_species.index)
    matched = pd.Series(False, index=raw_species.index)
    # "hainbuche" contains "buche" as a substring, so check it first — order
    # of dict insertion is preserved in Python 3.7+, but iterate explicitly to
    # keep this correct regardless.
    for keyword in ["hainbuche", *[k for k in REAL_SPECIES_KEYWORDS if k != "hainbuche"]]:
        genus = REAL_SPECIES_KEYWORDS[keyword]
        hit = (~matched) & lowered.str.contains(keyword, na=False)
        bucket = bucket.where(~hit, genus)
        matched |= hit
    return bucket

EMISSIONS_COLUMN_ALIASES = {
    "PLZ": ["plz", "postleitzahl", "postal_code", "zip"],
    "total_co2_tons": ["total_co2_tons", "co2_tons", "co2_t", "emissions_tons", "ghg_tons"],
    "population_density": ["population_density", "einwohnerdichte", "pop_density"],
    "sealed_surface_ratio": ["sealed_surface_ratio", "versiegelungsgrad", "sealed_ratio"],
}


def find_real_trees_csv() -> Path | None:
    if REAL_TREES_CSV.exists():
        return REAL_TREES_CSV
    if REAL_TREES_FALLBACK_DIR.exists():
        matches = sorted(REAL_TREES_FALLBACK_DIR.glob(REAL_TREES_FALLBACK_GLOB))
        if matches:
            print(f"load_real_data: {REAL_TREES_CSV} not found, using {matches[0]} instead "
                  f"(matched data/raw/{REAL_TREES_FALLBACK_GLOB}). Consider moving it to "
                  f"{REAL_TREES_CSV} for clarity.")
            return matches[0]
    return None


def try_load_real_trees(plz_gdf: gpd.GeoDataFrame, current_year: int) -> pd.DataFrame | None:
    """Load + normalize a real tree export if present, spatially joined to
    real PLZ polygons. Returns None (not an empty DataFrame) if no file is
    present, so callers can distinguish "no real data" from "empty result"."""
    source_path = find_real_trees_csv()
    if source_path is None:
        return None

    raw = pd.read_csv(source_path)
    cols = TREE_COLUMN_ALIASES

    species_col = _first_matching_column(raw, cols["species"])
    year_col = _first_matching_column(raw, cols["planting_year"])
    diam_col = _first_matching_column(raw, cols["trunk_diameter_cm"])
    circ_col = _first_matching_column(raw, cols["trunk_circumference_cm"])
    lat_col = _first_matching_column(raw, cols["latitude"])
    lon_col = _first_matching_column(raw, cols["longitude"])
    x_col = _first_matching_column(raw, cols["x"])
    y_col = _first_matching_column(raw, cols["y"])

    missing = []
    if species_col is None:
        missing.append("species/genus")
    if year_col is None:
        missing.append("planting year")
    if diam_col is None and circ_col is None:
        missing.append("trunk diameter or circumference")
    if (lat_col is None or lon_col is None) and (x_col is None or y_col is None):
        missing.append("coordinates (lat/lon or x/y)")

    if missing:
        raise ValueError(
            f"{source_path} was found but is missing recognizable columns for: "
            f"{', '.join(missing)}. Found columns: {list(raw.columns)}. "
            "Add/rename columns to match one of the aliases in TREE_COLUMN_ALIASES "
            "in load_real_data.py, or extend that list for your export's actual "
            "column names."
        )

    df = pd.DataFrame()
    raw_species = raw[species_col].astype(str)
    df["species"] = _normalize_species_to_genus(raw_species)
    n_other = (df["species"] == SPECIES_OTHER_BUCKET).sum()
    print(f"load_real_data: normalized {raw_species.nunique():,} distinct real species names down to "
          f"{df['species'].nunique()} genus buckets ({n_other:,}/{len(df):,} = {n_other/max(len(df),1)*100:.1f}% "
          f"fell into '{SPECIES_OTHER_BUCKET}').")
    df["planting_year"] = pd.to_numeric(raw[year_col], errors="coerce")

    if diam_col is not None:
        df["trunk_diameter_cm"] = pd.to_numeric(raw[diam_col], errors="coerce")
    else:
        # Circumference -> diameter: d = circumference / pi
        df["trunk_diameter_cm"] = pd.to_numeric(raw[circ_col], errors="coerce") / np.pi

    if lat_col is not None and lon_col is not None:
        lat = pd.to_numeric(raw[lat_col], errors="coerce")
        lon = pd.to_numeric(raw[lon_col], errors="coerce")
    else:
        # Projected coordinates. Detect which CRS by magnitude — this matters
        # a lot: guessing wrong silently places every tree in the wrong spot.
        #   - lat/lon: values always < 180
        #   - EPSG:25833 (ETRS89/UTM 33N, standard for Berlin official
        #     geodata): easting ~300,000-500,000, northing ~5,700,000-6,000,000
        #     for Berlin specifically
        #   - EPSG:3857 (Web Mercator): easting ~1,400,000-1,600,000, northing
        #     ~6,800,000-6,950,000 for Berlin specifically. Confirmed by
        #     spot-checking: Berlin's real Baumkataster export
        #     (Baumkataster_Berlin_*.csv) uses this, NOT EPSG:25833, despite
        #     25833 being the more commonly-assumed default for German geodata
        #     — don't assume, check.
        x_vals = pd.to_numeric(raw[x_col], errors="coerce")
        y_vals = pd.to_numeric(raw[y_col], errors="coerce")
        x_median = x_vals.abs().median()
        if x_median > 1_000_000:
            source_crs = "EPSG:3857"
        elif x_median > 1_000:
            source_crs = "EPSG:25833"
        else:
            source_crs = None

        if source_crs:
            pts = gpd.GeoSeries(gpd.points_from_xy(x_vals, y_vals), crs=source_crs).to_crs("EPSG:4326")
            lon, lat = pts.x, pts.y
            print(f"load_real_data: detected tree coordinates as {source_crs} (x median magnitude {x_median:,.0f}), reprojected to EPSG:4326.")
        else:
            lon, lat = x_vals, y_vals

    df["latitude"] = lat
    df["longitude"] = lon

    before = len(df)
    df = df.dropna(subset=["species", "planting_year", "trunk_diameter_cm", "latitude", "longitude"])
    dropped = before - len(df)
    if dropped:
        print(f"load_real_data: dropped {dropped}/{before} real tree rows with missing/unparseable fields.")

    df["tree_id"] = range(1, len(df) + 1)

    # Spatial join to REAL PLZ polygons — real cadastre exports come with
    # Bezirk/Ortsteil/coordinates, not a ready-made PLZ column.
    points_gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs="EPSG:4326"
    )
    joined = gpd.sjoin(points_gdf, plz_gdf[["PLZ", "geometry"]], how="inner", predicate="within")
    joined = joined.drop(columns=["geometry", "index_right"])
    joined["PLZ"] = joined["PLZ"].astype(str)

    unmatched = len(points_gdf) - len(joined)
    if unmatched:
        print(f"load_real_data: {unmatched} real trees fell outside all PLZ polygons and were dropped.")

    return joined[["tree_id", "species", "planting_year", "trunk_diameter_cm", "latitude", "longitude", "PLZ"]]


def try_load_real_emissions(plz_gdf: gpd.GeoDataFrame) -> pd.DataFrame | None:
    """Load + normalize a real PLZ-level emissions file if present. Returns
    None if no file is present — this loader intentionally does not attempt
    Bezirk->PLZ disaggregation (see module docstring)."""
    if not REAL_EMISSIONS_CSV.exists():
        return None

    raw = pd.read_csv(REAL_EMISSIONS_CSV)
    cols = EMISSIONS_COLUMN_ALIASES

    plz_col = _first_matching_column(raw, cols["PLZ"])
    co2_col = _first_matching_column(raw, cols["total_co2_tons"])

    if plz_col is None or co2_col is None:
        raise ValueError(
            f"{REAL_EMISSIONS_CSV} was found but is missing a recognizable PLZ or "
            f"CO2 column. Found columns: {list(raw.columns)}. Expected a PLZ "
            "identifier column and a total-CO2-tons column — see "
            "EMISSIONS_COLUMN_ALIASES in load_real_data.py."
        )

    df = pd.DataFrame()
    df["PLZ"] = raw[plz_col].astype(str)
    df["total_co2_tons"] = pd.to_numeric(raw[co2_col], errors="coerce")

    pop_col = _first_matching_column(raw, cols["population_density"])
    sealed_col = _first_matching_column(raw, cols["sealed_surface_ratio"])
    df["population_density"] = pd.to_numeric(raw[pop_col], errors="coerce") if pop_col else np.nan
    df["sealed_surface_ratio"] = pd.to_numeric(raw[sealed_col], errors="coerce") if sealed_col else np.nan

    valid_plz = set(plz_gdf["PLZ"].astype(str))
    before = len(df)
    df = df[df["PLZ"].isin(valid_plz)]
    if len(df) < before:
        print(f"load_real_data: dropped {before - len(df)} emissions rows with PLZ not present in the real PLZ boundaries.")

    return df.dropna(subset=["total_co2_tons"])


def try_load_real_population(plz_gdf: gpd.GeoDataFrame) -> pd.DataFrame | None:
    """Load real PLZ-level population if present (data/external/real/plz_einwohner.csv,
    a nationwide German PLZ/population lookup — filtered here to the PLZ codes
    actually present in plz_gdf). Returns a DataFrame with PLZ, population_density
    (people/km2, computed as einwohner/qkm), and einwohner (raw headcount), or
    None if the file isn't present. This does NOT make emissions real — see the
    module docstring — but it replaces a fabricated population figure with a
    real one."""
    if not REAL_POPULATION_CSV.exists():
        return None

    raw = pd.read_csv(REAL_POPULATION_CSV, dtype={"plz": str})
    plz_col = _first_matching_column(raw, ["plz", "PLZ", "postal_code", "zip"])
    pop_col = _first_matching_column(raw, ["einwohner", "population", "inhabitants"])
    area_col = _first_matching_column(raw, ["qkm", "area_km2", "area_sqkm"])

    if plz_col is None or pop_col is None or area_col is None:
        raise ValueError(
            f"{REAL_POPULATION_CSV} was found but is missing a recognizable PLZ, "
            f"population, or area column. Found columns: {list(raw.columns)}."
        )

    df = pd.DataFrame()
    df["PLZ"] = raw[plz_col].astype(str).str.strip()
    df["einwohner"] = pd.to_numeric(raw[pop_col], errors="coerce")
    area_km2 = pd.to_numeric(raw[area_col], errors="coerce")
    df["population_density"] = df["einwohner"] / area_km2.replace(0, np.nan)

    valid_plz = set(plz_gdf["PLZ"].astype(str))
    before = len(df)
    df = df[df["PLZ"].isin(valid_plz)].dropna(subset=["population_density"])
    print(f"load_real_data: matched {len(df)}/{len(valid_plz)} real PLZ boundaries to real population rows "
          f"(source file has {before} total PLZ rows nationwide, most of which aren't in Berlin).")

    return df[["PLZ", "einwohner", "population_density"]]


def try_load_real_bezirk_emissions() -> pd.DataFrame | None:
    """Load real Bezirk-level (borough) CO2 emissions if data/external/real/
    bezirk_emissions.csv is present. Returns a DataFrame with columns bezirk,
    total_co2_tons, year, source_url — for boroughs Berlin hasn't published a
    figure for, total_co2_tons is NaN (Berlin does not publish a complete
    borough-level GHG dataset; confirmed via an official parliamentary
    written response — see BEZIRK_EMISSIONS_PROVENANCE.md for the full
    citation and caveats, including that the 2 populated rows are from
    different years and are NOT summable into a citywide total). Returns
    None only if the file itself is missing."""
    if not REAL_BEZIRK_EMISSIONS_CSV.exists():
        return None
    df = pd.read_csv(REAL_BEZIRK_EMISSIONS_CSV)
    df["total_co2_tons"] = pd.to_numeric(df["total_co2_tons"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    n_real = df["total_co2_tons"].notna().sum()
    print(f"load_real_data: real Bezirk-level CO2 data available for {n_real}/{len(df)} boroughs "
          "(Berlin has not published figures for the rest — see BEZIRK_EMISSIONS_PROVENANCE.md).")
    return df[["bezirk", "total_co2_tons", "year", "source_url"]]
