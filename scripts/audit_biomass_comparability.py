#!/usr/bin/env python3
"""Read-only quality audit of published biomass preview metadata.

This is deliberately NOT a calculation of tonnes of biomass.  It reports
what must be verified in the native source GeoTIFFs before area integration.
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "docs/data/preview/preview_layers.json").read_text(encoding="utf-8"))
stat = json.loads((root / "docs/data/preview/preview_statistics.json").read_text(encoding="utf-8"))
names = {"2010": "biomass_2010", "2015": "biomass_2015_leaf", "2018": "biomass"}
assert manifest["layers"] and stat["layers"]
print("Year | Source pixel (m) | CRS | band unit | scale | offset | preview p98 | preview max | status")
for year, key in names.items():
    m = manifest["layers"][key]
    s = stat["layers"][key]
    assert m["source"] == s["source"], f"source mismatch: {key}"
    assert m["raster_grid_crs"] == "EPSG:3857"
    assert m["source_year"] == int(year)
    res = m["source_resolution_m"]
    source_crs = m["source_crs"]
    band_unit = m.get("source_unit_tag")
    scale = m.get("source_band_scale")
    offset = m.get("source_band_offset")
    p98, vmax = s["p98_raw"], s["max_raw"]
    flags = []
    if not band_unit:
        flags.append("native-band-unit-unverified")
    if not m.get("physical_units_verified", False):
        flags.append("physical-scaling-unverified")
    if p98 > 0 and vmax > 20 * p98:
        flags.append("extreme-upper-tail-review")
    print(f"{year} | {res} | {source_crs[-48:]} | {band_unit} | {scale} | {offset} | {p98} | {vmax} | {','.join(flags) or 'metadata-ok'}")
print("No tonne totals or comparability claims generated.")
