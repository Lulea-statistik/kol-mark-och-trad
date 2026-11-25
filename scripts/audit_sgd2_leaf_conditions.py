#!/usr/bin/env python3
"""Audit leaf-on/off scan assessment for exact SGD2 omdrev-2 Lulea tiles.

Queries the SAME older GIS service as scripts/audit_sgd2_scan_dates.py,
NOT the newer SGD3 service referenced in the 2026 product description.
Missing Lov_Avlov is UNKNOWN. Never infer leaf status from month alone.
"""
import collections
import datetime as dt
import json
import pathlib
import re
import sys

from shapely.geometry import Point, Polygon, shape
from shapely.ops import unary_union

from audit_sgd2_scan_dates import SERVICE, request, year_values, ROOT

OUTPUT = ROOT / "docs/data/sgd2_lulea_leaf_conditions.json"

def find_leaf_field(fields):
    """Do not silently mistake other metadata for leaf condition."""
    for original in fields.values():
        canonical = original.casefold().replace("_", "").replace("ö", "o")
        if canonical == "lovavlov":
            return original
    return None

def classify_leaf(value):
    if value is None or str(value).strip() == "":
        return "unknown"
    try:
        code = int(value)
    except (ValueError, TypeError):
        return "unknown"
    return {1: "leaf_on", 2: "leaf_off"}.get(code, "unknown")

def parse_month(value):
    if isinstance(value, (int, float)) and value > 10**11:
        return dt.datetime.fromtimestamp(value/1000, dt.timezone.utc).strftime("%Y-%m")
    match = re.search(r"(?<!\d)(20\d{2})[-/]?(0[1-9]|1[0-2])", str(value or ""))
    return match.group(1)+"-"+match.group(2) if match else "unknown"

def main():
    boundary=json.loads((ROOT/"docs/data/lulea_boundary.geojson").read_text(encoding="utf-8"))
    if boundary["crs"]["properties"]["name"]!="EPSG:4326":
        raise ValueError("Municipal working boundary CRS must be explicitly EPSG:4326")
    polygon=unary_union([shape(f["geometry"]) for f in boundary["features"]])
    if not polygon.is_valid:
        raise ValueError("Invalid municipality boundary")
    xmin,ymin,xmax,ymax=polygon.bounds
    layer=request(SERVICE,{"f":"json"})
    fields={f["name"].casefold():f["name"] for f in layer["fields"]}
    for required in ("datum","omdrev","centerkommunnamn"):
        if required not in fields:
            raise ValueError("Expected SGD2 metadata field missing: "+required)
    leaf_field=find_leaf_field(fields)
    common={"f":"json","where":"1=1",
            "geometry":",".join(map(str,(xmin,ymin,xmax,ymax))),
            "geometryType":"esriGeometryEnvelope","inSR":4326,
            "spatialRel":"esriSpatialRelIntersects"}
    ids=request(SERVICE+"/query",dict(common,returnIdsOnly="true"))
    object_ids=ids.get("objectIds") or []
    oid_field=ids.get("objectIdFieldName") or layer.get("objectIdField")
    if not object_ids or not oid_field:
        raise ValueError("SGD2 service returned no matching metadata tiles")
    status=collections.Counter()
    months=collections.Counter()
    dates=collections.Counter()
    rows=[]
    for start in range(0,len(object_ids),150):
        data=request(SERVICE+"/query",{
             "f":"json","objectIds":",".join(map(str,object_ids[start:start+150])),
             "outFields":"*","returnGeometry":"true","outSR":4326})
        for item in data.get("features",[]):
            a=item.get("attributes",{})
            if "lule" not in str(a.get(fields["centerkommunnamn"],"")).casefold():
                continue
            cycle=str(a.get(fields["omdrev"],"")).strip().casefold()
            if cycle!="2" and "omdrev 2" not in cycle and "omdrev2" not in cycle:
                continue
            g=item.get("geometry") or {}
            if "rings" in g:
                intersects=any(p.is_valid and p.intersects(polygon)
                       for p in (Polygon(r) for r in g["rings"] if len(r)>=4))
            elif "x" in g and "y" in g:
                intersects=polygon.intersects(Point(g["x"],g["y"]))
            else:
                intersects=False
            if not intersects:continue
            ys=sorted(set(year_values(a.get(fields["datum"]))))
            if ys!=[2018]:
                raise ValueError("Unexpected SGD2 local scan year: "+str(ys))
            leaf=classify_leaf(a.get(leaf_field) if leaf_field else None)
            month=parse_month(a.get(fields["datum"]))
            status[leaf]+=1
            months[(month,leaf)]+=1
            dates[month]+=1
            rows.append({"id":a.get(oid_field),"month":month,"leaf_status":leaf})
    if not rows:raise ValueError("No SGD2 omdrev-2 data verified for Lulea")
    if sum(status.values())!=len(rows):
        raise ValueError("Unreconciled records by leaf condition")
    payload={
        "source":SERVICE,
        "raster":"https://gis.slu.se/data/slu_skogliga_grunddata/SGD2/data/SGD2_BIO.tif",
        "product":"SGD2 omdrev 2 only; NOT SGD3",
        "retrieved_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "boundary":"docs/data/lulea_boundary.geojson",
        "boundary_crs":"EPSG:4326",
        "service_query_crs":"EPSG:4326",
        "source_metadata_field":leaf_field,
        "leaf_status_available":leaf_field is not None,
        "verified_scan_year":2018,
        "tile_record_count":len(rows),
        "leaf_condition_counts":dict(sorted(status.items())),
        "month_condition_counts":[{"month":m,"condition":c,"records":n}
                                  for (m,c),n in sorted(months.items())],
        "monthly_record_counts":dict(sorted(dates.items())),
        "status":("MEASURED_SGD2_LEAF_CONDITION_BY_METADATA_RECORD"
                  if leaf_field is not None
                  else "LEAF_CONDITION_NOT_AVAILABLE_IN_SGD2_SERVICE_NO_MONTH_IMPUTATION"),
        "limitations":[
          "Counts are scan-metadata records, not area and not SGD2 biomass-cell percentages",
          "Lov_Avlov describes assessment of scan conditions, not inclusion of deciduous foliage in dry mass",
          "2018 scanned period only, with possible different dates within each 2.5km metadata tile",
          "No causal effect or bias magnitude can be estimated from a leaf-status group mean",
          "Do not interpret this as comparison to SGD3 or to SLU Skogskarta 2015",
          "Some tiles are represented as centroids; clipped overlaps are not area-weighted"],
        "records":rows
    }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Leaf condition source field:",leaf_field)
    print("Records:",len(rows),"conditions:",dict(status),"monthly:",dict(dates))
    print("Status:",payload["status"])
if __name__=="__main__":
    main()
