#!/usr/bin/env python3
"""Publish original-CRS sample footprints as WGS84 GeoJSON for Leaflet review.

No biomass values are changed. Snapshot is only the 221 probabilistic samples
and risk queue. EPSG:3006 is asserted from the audit before transformation.
Coordinates are sampled source pixel centers; actual cell footprints use the
native source transform rather than an unverified 10m square approximation.
"""
import csv
import json
from pathlib import Path
from pyproj import Transformer
from rasterio.transform import Affine

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/"metadata/nmd2018_biomass_lulea_audit.json"
STRAT=ROOT/"metadata/biomass_stratified_validation_sample_epsg3006.csv"
RISK=ROOT/"metadata/biomass_independent_review_register.csv"
OUTPUT=ROOT/"docs/data/biomass_review_snapshot.geojson"
PORTS=[
 {"name":"Isbrytarhamn, kontrollpunkt A","lon":22.171025,"lat":65.571144},
 {"name":"Isbrytarhamn, kontrollpunkt B","lon":22.170352,"lat":65.572057}
]
def create():
    p=json.loads(AUDIT.read_text(encoding="utf-8"))
    metadata=p["results"]["metadata"]
    if metadata.get("sgd2_epsg") != 3006 or metadata.get("nmd_epsg") != 3006:
        # Current legacy metadata may give WKT rather than EPSG string.
        from rasterio.crs import CRS
        def epsg3006(value):
            crs=CRS.from_user_input(value)
            return crs.to_epsg()==3006 or ('AUTHORITY["EPSG","3006"]' in crs.to_wkt() and "SWEREF99 TM" in crs.to_wkt())
        if not epsg3006(metadata["crs_sgd2"]) or not epsg3006(metadata["crs_nmd"]):
            raise ValueError("Original CRS not verifiably EPSG:3006")
    transformer=Transformer.from_crs("EPSG:3006","EPSG:4326",always_xy=True)
    # Use the exact source transform added to audit metadata, no assumptions.
    affine6=metadata.get("sgd2_transform")
    if not affine6 or len(affine6)!=6:raise ValueError("Missing actual source raster affine transform")
    transform=Affine(*affine6)
    inverse=~transform
    features=[]
    known={}
    def add(row,origin):
        x,y=float(row["east_epsg3006"]),float(row["north_epsg3006"])
        col,rowix=inverse*(x,y)
        c=int(col); r=int(rowix)
        key=(r,c)
        # Avoid duplicate features when the targeted and random sets overlap.
        if key in known:
            known[key]["properties"]["origins"].append(origin)
            return
        corners=[transform*(c, r), transform*(c+1,r),
                 transform*(c+1,r+1),transform*(c,r+1)]
        ring=[list(transformer.transform(xx,yy)) for xx,yy in corners]
        ring.append(ring[0])
        prop={"origin":origin,"origins":[origin],"east_epsg3006":x,
              "north_epsg3006":y,"raw_biomass":float(row["raw_biomass"]),
              "nmd_code":int(row["nmd_code"]),"review_status":"not_reviewed",
              "source_crs_epsg":3006,"footprint":"actual SGD2 native pixel grid"}
        if origin=="random":
            for k in ("stratum","population_n","sample_n","inclusion_probability"):
                prop[k]=row[k]
        else:
            prop["flag_rules"]=row["flag_rules"]
        feature={"type":"Feature","geometry":{"type":"Polygon","coordinates":[ring]},
                 "properties":prop}
        known[key]=feature;features.append(feature)
    with STRAT.open(newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):add(row,"random")
    with RISK.open(newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):add(row,"risk")
    for port in PORTS:
        features.append({"type":"Feature","geometry":{"type":"Point","coordinates":[port["lon"],port["lat"]]},
             "properties":{"origin":"harbor_hypothesis","name":port["name"],
               "observation":"User notes icebreakers may berth here and can be mistaken for vegetation in height-based data",
               "source_crs":"degrees, interpreted as WGS84 EPSG:4326; datum not independently verified",
               "review_status":"hypothesis_unverified",
               "note":"Not confirmed vessel presence or erroneous SGD2 biomass; inspect photo acquisition date and exact cell locations"}})
    result={"type":"FeatureCollection","metadata":{
        "audit_timestamp":p["checked_at_utc"],"input_source_crs":"EPSG:3006",
        "web_display_crs":"EPSG:4326",
        "original_raster_modified":False,
        "independent_errors_confirmed":0,
        "note":"Map is review aid only; not verified errors or edited raster"},
        "features":features}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print("Review map snapshot",len(features),"features",len(known),"distinct original cells")
if __name__=="__main__":create()
