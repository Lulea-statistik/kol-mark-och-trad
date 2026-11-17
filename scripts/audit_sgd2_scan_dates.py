#!/usr/bin/env python3
"""Inventory SGD2 scanning dates intersecting the working Lulea boundary.

Do not infer a scanning year from the file's creation date or the SGD2 product name.
Requires Skogsstyrelsen ArcGIS MapServer to be reachable from GitHub Actions.
"""
import collections
import datetime as dt
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVICE = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSkogligaGrunddataMetadata/MapServer/0"
OUTPUT = ROOT / "docs/data/sgd2_lulea_scan_years.json"

def request(endpoint, params):
    url = endpoint + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Lulea-statistik-SGD2-date-audit/1.0"}), timeout=45) as response:
                result = json.load(response)
            if "error" in result:
                raise RuntimeError(str(result["error"]))
            return result
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

def year_values(value):
    if value is None or value == "":
        return []
    if isinstance(value, (int, float)) and value > 10**11:
        return [dt.datetime.fromtimestamp(value / 1000, dt.timezone.utc).year]
    if isinstance(value, (int, float)) and 1900 <= value <= 2100:
        return [int(value)]
    return [int(y) for y in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", str(value)) if 2000 <= int(y) <= 2100]

def main():
    boundary = json.loads((ROOT / "docs/data/lulea_boundary.geojson").read_text(encoding="utf-8"))
    assert boundary["crs"]["properties"]["name"] == "EPSG:4326", "Verify input boundary CRS"
    lulea = unary_union([shape(f["geometry"]) for f in boundary["features"]])
    xmin, ymin, xmax, ymax = lulea.bounds
    layer = request(SERVICE, {"f": "json"})
    fields = {f["name"].casefold(): f["name"] for f in layer["fields"]}
    for required in ("datum", "omdrev", "centerkommunnamn"):
        if required not in fields:
            raise RuntimeError("Missing expected field " + required + "; available fields: " + ", ".join(fields.values()))
    datum, omdrev, kommun = (fields[s] for s in ("datum", "omdrev", "centerkommunnamn"))
    common = {
        "f": "json", "where": "1=1", "geometry": ",".join(map(str, (xmin, ymin, xmax, ymax))),
        "geometryType": "esriGeometryEnvelope", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects"
    }
    ids = request(SERVICE + "/query", dict(common, returnIdsOnly="true"))
    object_ids = ids.get("objectIds") or []
    oid_field = ids.get("objectIdFieldName") or layer.get("objectIdField")
    if not object_ids or not oid_field:
        raise RuntimeError("No feature ids returned by metadata service: do not overwrite existing data.")
    by_year = collections.Counter()
    rows = 0
    missing_date = 0
    selected = []
    for index in range(0, len(object_ids), 150):
        batch = request(SERVICE + "/query", {
            "f": "json", "objectIds": ",".join(str(n) for n in object_ids[index:index + 150]),
            "outFields": "*", "returnGeometry": "true", "outSR": 4326
        })
        for feature in batch.get("features", []):
            a = feature.get("attributes", {})
            if "lule" not in str(a.get(kommun, "")).casefold():
                continue
            cycle = str(a.get(omdrev, "")).strip().casefold()
            if not (cycle == "2" or "omdrev 2" in cycle or "omdrev2" in cycle):
                continue
            geom = feature.get("geometry", {})
            # Some layers store grid footprints as polygons, others only grid centroids.
            # Only count records that demonstrably intersect the working municipality boundary.
            if "rings" in geom:
                from shapely.geometry import Polygon
                parts = [Polygon(ring) for ring in geom["rings"] if len(ring) >= 4]
                intersects = any(p.is_valid and p.intersects(lulea) for p in parts)
            elif "x" in geom and "y" in geom:
                from shapely.geometry import Point
                intersects = lulea.intersects(Point(geom["x"], geom["y"]))
            else:
                intersects = False
            if not intersects:
                continue
            rows += 1
            years = sorted(set(year_values(a.get(datum))))
            if not years:
                missing_date += 1
            for year in years:
                by_year[year] += 1
            selected.append({"id": a.get(oid_field), "date": a.get(datum), "years": years})
    if not rows or not by_year:
        raise RuntimeError("No dated SGD2 Lulea records verified; leave existing metadata unchanged.")
    payload = {
        "source": SERVICE, "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "raster": "https://gis.slu.se/data/slu_skogliga_grunddata/SGD2/data/SGD2_BIO.tif",
        "boundary": "docs/data/lulea_boundary.geojson",
        "boundary_status": "working geometry, not an official legal municipality boundary",
        "boundary_crs": "EPSG:4326", "query_crs": "EPSG:4326",
        "omdrev": 2, "method": "ArcGIS metadata tiles: CenterKommunNamn matches Lulea, Omdrev equals 2, geometry intersects working boundary",
        "date_field": datum, "record_count": rows, "records_without_date": missing_date,
        "year_counts": dict(sorted(by_year.items())),
        "dominant_year_by_record_count": by_year.most_common(1)[0][0],
        "dominant_year_caveat": "Number of overlapping metadata features, NOT area-weighted coverage or a single year for every raster cell.",
        "multiple_years_per_record_possible": True,
        "records": selected
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("SGD2 scan year counts:", dict(sorted(by_year.items())))
    print("Records:", rows, "without dates:", missing_date)
    print("Written:", OUTPUT)

if __name__ == "__main__":
    main()
