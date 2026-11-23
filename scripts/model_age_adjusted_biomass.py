#!/usr/bin/env python3
"""Age-stratified biomass:total-volume conversion for 2000 and 2005.

On the SAME cells, derive age-bin biomass/volume ratios from the 2010 maps
and apply them to the native AGE and TOTALVOL of each historical year.
Not a growth rate. Not an independent or physically calibrated conversion.
Historical SLU 2005 biomass should be preferred if separately verified.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from contextlib import ExitStack
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from shapely.geometry import mapping,shape
from shapely.ops import transform as geom_transform
from pyproj import Transformer
from fetch_and_compare_biomass_native import matches_expected_crs
from analyze_historic_volume import validate_archive
from verify_biomass_release import run as verify_biomass
from analyze_forest_age_2010 import check_age

ROOT=Path(__file__).resolve().parents[1]
BINS=(0,20,40,60,80,100,120,150,200,300,500,float("inf"))
YEARS=("2000","2005","2010")
NAMES=("volume_2000","volume_2005","volume_2010",
       "age_2000","age_2005","age_2010","biomass_2010")
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(8*1024*1024),b""):h.update(block)
    return h.hexdigest()
def validate_historical_age(directory,boundary):
    output={}
    for year in ("2000","2005"):
        stem=f"lulea_forest_age_{year}"
        tif=directory/(stem+"_source_crs_clip.tif")
        proven=directory/(stem+"_provenance.json")
        check=directory/(stem+"_SHA256SUMS.txt")
        for f in (tif,proven,check):
            if not f.is_file() or not f.stat().st_size:raise ValueError(f"{year}: missing AGE release asset: {f}")
        lines=dict((name.strip(),h) for h,name in
                   (line.split(maxsplit=1) for line in check.read_text().splitlines() if line.strip()))
        for f in (tif,proven):
            if lines.get(f.name)!=sha(f):raise ValueError(f"{year}: SHA256 mismatch {f.name}")
        p=json.loads(proven.read_text(encoding="utf-8"))
        expected_url=f"https://gis.slu.se/data/slu_forest_map/{year}/Data/Raster/Rt90/AGE_XX_P_{year[-2:]}.tif"
        if str(p.get("year"))!=year or p.get("source_url")!=expected_url or p.get("boundary_sha256")!=sha(boundary):
            raise ValueError(f"{year}: AGE origin or municipal boundary differs")
        if p.get("asset_sha256")!=sha(tif) or p.get("asset_size_bytes")!=tif.stat().st_size:
            raise ValueError(f"{year}: AGE provenance mismatch")
        with rasterio.open(tif) as src:
            if src.count!=1 or not matches_expected_crs(src.crs,3021) or src.nodata!=-9999:
                raise ValueError(f"{year}: AGE native CRS/bands/NoData mismatch")
            if any(abs(abs(v)-25)>.05 for v in src.res):
                raise ValueError(f"{year}: AGE source resolution mismatch")
            if src.scales[0]!=1 or src.offsets[0]!=0:
                raise ValueError(f"{year}: AGE scale or offset unverified")
            total=0
            for _,window in src.block_windows(1):
                vals=src.read(1,window=window,masked=True).compressed()
                if len(vals) and (not np.isfinite(vals).all() or (vals<0).any()):
                    raise ValueError(f"{year}: invalid AGE values")
                total+=len(vals)
            if total!=p["valid_inside_polygon_pixels"]:
                raise ValueError(f"{year}: AGE valid count differs from provenance")
        output[year]={"sha256":sha(tif),"valid_native_cells":total}
    return output

def prepare(args):
    validate_archive(args.volume_dir,args.boundary)
    verify_biomass(argparse.Namespace(directory=args.biomass_dir,output=args.qa_output))
    check_age(args.age_2010_dir,args.boundary)
    return validate_historical_age(args.age_history_dir,args.boundary)

def run(args):
    age_info=prepare(args)
    doc=json.loads(args.boundary.read_text(encoding="utf-8"))
    if doc.get("type")!="FeatureCollection" or len(doc.get("features",[]))!=1:
        raise ValueError("One EPSG:4326 polygon required")
    source_polygon=shape(doc["features"][0]["geometry"])
    if not source_polygon.is_valid or source_polygon.is_empty:
        raise ValueError("Invalid project boundary")
    region=geom_transform(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,source_polygon)
    x0,y0,x1,y1=region.bounds;step=25.0
    x0=math.floor(x0/step)*step;y0=math.floor(y0/step)*step
    x1=math.ceil(x1/step)*step;y1=math.ceil(y1/step)*step
    width=round((x1-x0)/step);height=round((y1-y0)/step)
    if width*height>40_000_000:raise ValueError("Unexpected geometry extent")
    grid=Affine(step,0,x0,0,-step,y1)
    paths={}
    for year in YEARS:
        paths["volume_"+year]=args.volume_dir/f"lulea_total_volume_{year}_source_crs_clip.tif"
        paths["age_"+year]=(args.age_2010_dir if year=="2010" else args.age_history_dir)/f"lulea_forest_age_{year}_source_crs_clip.tif"
    paths["biomass_2010"]=args.biomass_dir/"lulea_biomass_2010_source_crs_clip.tif"

    bin_count=len(BINS)-1
    training=np.zeros((bin_count,3),dtype=np.float64) # cells, sum-volume, sum-biomass
    global_total=np.zeros(2,dtype=np.float64)
    samples=0
    def tile_iterator(vrts):
        for row in range(0,height,256):
            for col in range(0,width,256):
                win=Window(col,row,min(256,width-col),min(256,height-row))
                shape_=(int(win.height),int(win.width))
                mask=geometry_mask([mapping(region)],out_shape=shape_,
                                   transform=rasterio.windows.transform(win,grid),invert=True)
                if not mask.any():continue
                arrays={name:np.ma.asarray(vrt.read(1,window=win,masked=True),dtype="float64").filled(np.nan)
                        for name,vrt in vrts.items()}
                good=mask.copy()
                for a in arrays.values():good &= np.isfinite(a)&(a>=0)
                if not good.any():continue
                yield arrays,good

    with ExitStack() as stack:
        vrts={}
        for name,path in paths.items():
            src=stack.enter_context(rasterio.open(path))
            if src.count!=1 or src.nodata!=-9999 or not matches_expected_crs(src.crs,3021):
                raise ValueError(f"Unexpected source CRS or band for {name}")
            vrts[name]=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=grid,
                    width=width,height=height,src_nodata=src.nodata,nodata=-9999,
                    resampling=Resampling.average,dtype="float32"))
        for arrays,mask in tile_iterator(vrts):
            samples+=int(mask.sum())
            vol=arrays["volume_2010"][mask];bio=arrays["biomass_2010"][mask]
            age=arrays["age_2010"][mask]
            global_total[0]+=float(vol.sum());global_total[1]+=float(bio.sum())
            for i in range(bin_count):
                use=(age>=BINS[i])&(age<BINS[i+1])
                if not use.any():continue
                training[i,0]+=int(use.sum())
                training[i,1]+=float(vol[use].sum())
                training[i,2]+=float(bio[use].sum())
        if not samples or global_total[0]<=0:raise ValueError("Empty calibration data")
        global_factor=global_total[1]/global_total[0]
        min_count=args.min_bin_cells
        factors=[]
        rows=[]
        for i in range(bin_count):
            n,vol_sum,bio_sum=training[i]
            raw=bio_sum/vol_sum if vol_sum>0 else None
            # Shrink sparse classes towards global ratio instead of amplifying
            # small-sample variations. This is regularization, NOT uncertainty.
            weight=n/(n+min_count) if vol_sum>0 else 0.0
            used=weight*raw+(1-weight)*global_factor if raw is not None else global_factor
            factors.append(used)
            rows.append({"age_lower":BINS[i],
                         "age_upper":BINS[i+1] if math.isfinite(BINS[i+1]) else None,
                         "source_pixels":int(n),"raw_ratio":raw,
                         "shrinkage_weight":weight,"factor":used})
        ages=(2000,2005)
        estimate={year:{"sum_global":0.0,"sum_age_based":0.0,
                        "cells_by_bin":[0]*bin_count,"sum_volume":0.0} for year in ages}
        for arrays,mask in tile_iterator(vrts):
            for year in ages:
                vol=arrays[f"volume_{year}"][mask]
                age=arrays[f"age_{year}"][mask]
                estimate[year]["sum_global"]+=float(vol.sum())*global_factor
                estimate[year]["sum_volume"]+=float(vol.sum())
                for i in range(bin_count):
                    use=(age>=BINS[i])&(age<BINS[i+1])
                    estimate[year]["cells_by_bin"][i]+=int(use.sum())
                    if use.any():estimate[year]["sum_age_based"]+=float(vol[use].sum())*factors[i]
    history=[]
    for year in ages:
        e=estimate[year]
        history.append({"year":year,"data_type":"MODELLED_AGE_DEPENDENT",
                        "age_based_raw_mean":e["sum_age_based"]/samples,
                        "global_factor_raw_mean":e["sum_global"]/samples,
                        "relative_difference_percent":100*(e["sum_age_based"]/e["sum_global"]-1),
                        "share_cells_by_age_bin":[n/samples for n in e["cells_by_bin"]]})
    history.append({"year":2010,"data_type":"SOURCE_BIOMASS_RASTER",
                    "age_based_raw_mean":global_total[1]/samples,
                    "global_factor_raw_mean":global_total[1]/samples,
                    "relative_difference_percent":0.0})
    report={
      "created_utc":datetime.now(timezone.utc).isoformat(),
      "status":"PROVISIONAL_AGE_DEPENDENT_RAW_BIOMASS_MODEL",
      "reference_epoch":2010,
      "common_valid_cells":samples,"common_valid_area_ha":samples*.0625,
      "grid_crs":"EPSG:3006","cell_size_m":25,
      "historical_age_archive":age_info,
      "global_2010_ratio_of_sums":global_factor,
      "min_bin_cells_shrinkage_prior":min_count,
      "age_coefficients":rows,"historical_results":history,
      "limitations":[
        "AGE and TOTALVOL from each year are estimated SLU products, not ground-truth observations",
        "Age-specific biomass/volume from 2010 is cross-sectional and confounded by species and site quality",
        "No independently validated observed biomass for 2005 is used",
        "No cross-year change in real biomass or carbon stock can be inferred yet",
        "Only cells valid in all source rasters, no official municipal boundary or separate forest-land mask",
        "Sparse-bin shrinkage is regularization, not a confidence interval",
        "Source imaging years and biomass component definitions remain subject to verification"
      ]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--volume-dir",type=Path,default=Path("release-volume"))
    p.add_argument("--age-history-dir",type=Path,default=Path("release-age-history"))
    p.add_argument("--age-2010-dir",type=Path,default=Path("release-age-2010"))
    p.add_argument("--biomass-dir",type=Path,default=Path("release-biomass"))
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--qa-output",type=Path,default=Path("metadata/biomass_release_validation.json"))
    p.add_argument("--output",type=Path,default=Path("metadata/age_adjusted_biomass_2000_2005.json"))
    p.add_argument("--min-bin-cells",type=int,default=1000)
    args=p.parse_args()
    if args.min_bin_cells<=0:p.error("--min-bin-cells must be positive")
    run(args)
