#!/usr/bin/env python3
"""Evaluate 2010 stand age vs raw biomass and volume on identical EPSG:3006 cells.

This is a descriptive age-stratification, NOT a measured annual growth curve.
Validates all three archived release sources by SHA and original CRS first.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
from contextlib import ExitStack
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from pyproj import Transformer
from shapely.geometry import shape,mapping
from shapely.ops import transform as transform_geom
from analyze_historic_volume import validate_archive
from verify_biomass_release import run as verify_biomass
from fetch_and_compare_biomass_native import matches_expected_crs

AGE_BOUNDS=(0,20,40,60,80,100,120,150,200,300,500)
def sha(f):
    h=hashlib.sha256()
    with f.open("rb") as stream:
        for b in iter(lambda:stream.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()
def check_age(directory,boundary):
    stem="lulea_forest_age_2010"
    t=directory/(stem+"_source_crs_clip.tif")
    p=directory/(stem+"_provenance.json")
    checks=directory/(stem+"_SHA256SUMS.txt")
    expected={name:hashvalue for hashvalue,name in
              (line.split(maxsplit=1) for line in checks.read_text().splitlines() if line.strip())}
    for f in (t,p):
        if expected.get(f.name)!=sha(f):raise ValueError("Age archive SHA256 mismatch "+f.name)
    provenance=json.loads(p.read_text(encoding="utf-8"))
    if provenance["asset_sha256"]!=sha(t) or provenance["boundary_sha256"]!=sha(boundary):
        raise ValueError("Age archive provenance / working boundary mismatch")
    if provenance["source_url"]!="https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/AGE_XX_P_10.tif":
        raise ValueError("Age archive source URL mismatch")
    with rasterio.open(t) as src:
        if src.count!=1 or not matches_expected_crs(src.crs,3021) or src.nodata!=-9999:
            raise ValueError("Age native CRS or NoData invalid")
        if any(not math.isclose(abs(res),25,abs_tol=.05) for res in src.res):
            raise ValueError("Age native grid not 25 m")
        if src.scales[0]!=1 or src.offsets[0]!=0:
            raise ValueError("Unverified age native scale or offset")
        n=0
        for _,win in src.block_windows(1):
            a=src.read(1,window=win,masked=True).compressed()
            if a.size and (not np.isfinite(a).all() or (a<0).any()):
                raise ValueError("Invalid age source cell values")
            n+=int(a.size)
        if n!=provenance["valid_inside_polygon_pixels"]:
            raise ValueError("Unexpected valid age pixels")
    return {"sha256":sha(t),"source_crs":"EPSG:3021","valid_native_cells":n}

def run(args):
    # Full source-archive integrity check, not just checking GitHub workflow green.
    validate_archive(args.volume_dir,args.boundary)
    verify_biomass(argparse.Namespace(directory=args.biomass_dir,output=args.qa_output))
    age_archive=check_age(args.age_dir,args.boundary)
    boundary_doc=json.loads(args.boundary.read_text(encoding="utf-8"))
    poly=shape(boundary_doc["features"][0]["geometry"])
    if poly.is_empty or not poly.is_valid:raise ValueError("Invalid working boundary")
    geo=transform_geom(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,poly)
    x0,y0,x1,y1=geo.bounds
    cell=25.
    x0=math.floor(x0/cell)*cell;y0=math.floor(y0/cell)*cell
    x1=math.ceil(x1/cell)*cell;y1=math.ceil(y1/cell)*cell
    w=round((x1-x0)/cell);h=round((y1-y0)/cell)
    if w*h>40_000_000:raise ValueError("Unexpected working grid size")
    tf=Affine(cell,0,x0,0,-cell,y1)
    archives={
        "age":args.age_dir/"lulea_forest_age_2010_source_crs_clip.tif",
        "volume":args.volume_dir/"lulea_total_volume_2010_source_crs_clip.tif",
        "biomass":args.biomass_dir/"lulea_biomass_2010_source_crs_clip.tif"}
    classes={}
    for start,stop in zip(AGE_BOUNDS[:-1],AGE_BOUNDS[1:]):
        classes[f"{start}-{stop}"]={"age_lower_inclusive":start,"age_upper_exclusive":stop,
                              "cells":0,"sum_age":0.,"sum_volume":0.,"sum_biomass":0.,
                              "positive_volume":0,"positive_biomass":0}
    outside_age=0
    common=0
    with ExitStack() as stack:
        vrts={}
        for name,path in archives.items():
            src=stack.enter_context(rasterio.open(path))
            if not matches_expected_crs(src.crs,3021) or src.nodata!=-9999:
                raise ValueError("Unexpected archived source CRS/NoData "+name)
            vrts[name]=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=tf,width=w,height=h,
                   src_nodata=src.nodata,nodata=-9999,resampling=Resampling.average,dtype="float32"))
        for rr in range(0,h,256):
            for cc in range(0,w,256):
                win=Window(cc,rr,min(256,w-cc),min(256,h-rr))
                inside=geometry_mask([mapping(geo)],out_shape=(int(win.height),int(win.width)),
                       transform=rasterio.windows.transform(win,tf),invert=True)
                if not inside.any():continue
                values={name:np.ma.asarray(v.read(1,window=win,masked=True),
                          dtype="float64").filled(np.nan) for name,v in vrts.items()}
                valid=inside.copy()
                for a in values.values():valid &= np.isfinite(a)&(a>=0)
                if not valid.any():continue
                common+=int(valid.sum())
                age=values["age"]
                outside_age+=int(np.count_nonzero(valid & (age>=500)))
                for key,result in classes.items():
                    test=valid & (age>=result["age_lower_inclusive"]) & (age<result["age_upper_exclusive"])
                    count=int(test.sum())
                    if count==0:continue
                    result["cells"]+=count
                    for column,value in (("sum_age","age"),("sum_volume","volume"),("sum_biomass","biomass")):
                        result[column]+=float(values[value][test].sum(dtype="float64"))
                    result["positive_volume"]+=int(np.count_nonzero(values["volume"][test]>0))
                    result["positive_biomass"]+=int(np.count_nonzero(values["biomass"][test]>0))
    if not common:raise ValueError("No joint valid age-volume-biomass raster cells")
    rows=[]
    for key,r in classes.items():
        n=r["cells"]
        rows.append({"age_class_years":key,"count":n,"area_ha":n*.0625,
          "mean_age_raw":r["sum_age"]/n if n else None,
          "mean_volume_raw":r["sum_volume"]/n if n else None,
          "mean_biomass_raw":r["sum_biomass"]/n if n else None,
          "ratio_of_sums_biomass_to_volume":r["sum_biomass"]/r["sum_volume"] if r["sum_volume"] else None,
          "share_positive_volume":r["positive_volume"]/n if n else None,
          "share_positive_biomass":r["positive_biomass"]/n if n else None})
    output={"created_utc":datetime.now(timezone.utc).isoformat(),
       "status":"descriptive_not_growth_rate_not_verified_physical_mass",
       "archives":{"age_2010":age_archive},
       "working_geometry":"project working boundary, not verified official Lulea municipal boundary",
       "target_crs":"EPSG:3006","grid_resolution_m":25,
       "common_valid_cells":common,"common_valid_area_ha":common*.0625,
       "age_outside_0_500_cells":outside_age,
       "age_bin_rule":"Half-open intervals (years), age >=500 is excluded from classes but counted separately",
       "bins":rows,
       "warnings":[
         "Age cells after resampling are averaged raster AGE estimates, not verified chronological stand ages",
         "Cross-sectional age vs biomass is NOT growth over time; site quality, species and harvest history confound the relationship",
         "2010 biomass and volume are related model products, not independent validation",
         "All means are raw values; no physical conversion or carbon inference is authorized",
         "No verified forest-land mask; zero biomass or volume may represent nonforest cells"
       ]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(output,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--age-dir",type=Path,default=Path("release-age"))
    p.add_argument("--volume-dir",type=Path,default=Path("release-volume"))
    p.add_argument("--biomass-dir",type=Path,default=Path("release-biomass"))
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--qa-output",type=Path,default=Path("metadata/biomass_release_validation.json"))
    p.add_argument("--output",type=Path,default=Path("metadata/forest_age_2010_volume_biomass_profile.json"))
    run(p.parse_args())
