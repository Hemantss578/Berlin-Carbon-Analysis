# Source: real Berlin borough (Bezirk) boundaries

- Origin: https://github.com/m-hoerz/berlin-shapes (fetched via raw.githubusercontent.com)
- Underlying source: Statistical Office of Berlin-Brandenburg official shapefiles
  (https://www.statistik-berlin-brandenburg.de/produkte/opendata/geometrienOD.asp?Kat=6301),
  boroughs derived by merging official locality ("Ortsteil") shapes.
- License: CC-BY 3.0 DE (http://creativecommons.org/licenses/by/3.0/de/) — attribution required.
- Content: 12 real Berlin boroughs, already in EPSG:4326, with a `spatial_alias`
  property holding the real borough name (e.g. "Mitte", "Pankow", "Charlottenburg-Wilmersdorf").
- Used in app.py to label the map with real, human-readable area names instead
  of bare PLZ numbers, and to draw borough outlines instead of a solid PLZ choropleth.
