#!/usr/bin/env python3
"""Refresh manual review annotations without opening remote SGD2 raster.

Keep source sample polygons and their audit timestamp intact. Only annotations
and additional user observation points are recreated. No raster modification.
"""
import csv
import json
from pathlib import Path
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
GEO=ROOT/"docs/data/biomass_review_snapshot.geojson"
CSV=ROOT/"docs/data/biomass_user_observations_epsg3006.csv"

def refresh():
    data=json.loads(GEO.read_text(encoding="utf-8"))
    md=data["metadata"]
    if md.get("input_source_crs")!="EPSG:3006" or md.get("web_display_crs")!="EPSG:4326":
        raise ValueError("Unexpected published coordinate systems; do not guess CRS")
    if md.get("original_raster_modified") is not False:
        raise ValueError("Map must not assert source raster mutation")
    with CSV.open(newline="",encoding="utf-8") as file:
        observations=list(csv.DictReader(file))
    keys=[(float(r["east_epsg3006"]),float(r["north_epsg3006"])) for r in observations]
    if len(set(keys))!=len(keys):
        raise ValueError("Duplicate manual observation coordinates")
    transformer=Transformer.from_crs("EPSG:3006","EPSG:4326",always_xy=True)
    features=[]
    existing={}
    for feature in data["features"]:
        p=feature["properties"]
        if p.get("origin")=="user_observation":
            continue
        if "user_observation" in p:
            del p["user_observation"]
        if "user_observation" in p.get("origins",[]):
            p["origins"]=[x for x in p["origins"] if x!="user_observation"]
        if feature["geometry"]["type"]=="Polygon":
            key=(float(p["east_epsg3006"]),float(p["north_epsg3006"]))
            if key in existing:
                raise ValueError("Duplicate sample cell centers in published map")
            existing[key]=feature
        features.append(feature)
    for r in observations:
        x,y=float(r["east_epsg3006"]),float(r["north_epsg3006"])
        reviewed=r["observation_status"]=="user_individually_reviewed"
        detail={"origin":"user_observation","origins":["user_observation"],
                "east_epsg3006":x,"north_epsg3006":y,
                "reported_context":r["reported_context"],"cluster":r["cluster"],
                "review_status":r["observation_status"],"individually_reviewed":reviewed,
                "manual_plausibility_assessment":r["manual_plausibility_assessment"],
                "observation_note":r["observation_note"],"evidence_source":r["source"],
                "independently_confirmed":False}
        if (x,y) in existing:
            p=existing[(x,y)]["properties"]
            p["origins"].append("user_observation")
            p["user_observation"]=detail
        else:
            lon,lat=transformer.transform(x,y)
            features.append({"type":"Feature","geometry":{"type":"Point","coordinates":[lon,lat]},
                             "properties":detail})
    data["features"]=features
    md["manual_observations_count"]=len(observations)
    md["manual_review_annotations_refreshed_without_raster_download"]=True
    md["note"]="Existing original-grid sample geometry reused; manual observations refreshed without rerunning raster analysis; no independent errors confirmed."
    GEO.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(f"Updated {len(observations)} manual review annotations; original audit {md.get('audit_timestamp')} retained")

if __name__=="__main__":
    refresh()
