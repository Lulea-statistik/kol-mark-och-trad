#!/usr/bin/env python3
"""Cross NMD2018 classes with 2010 volume and biomass on one EPSG:3006 grid.

No EPSG:3857 preview is used for area or biomass calculations.
All classes are fixed NMD2018 labels; not historical 2010 land-use observations.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform as geom_transform
from compare_biomass_native_area import matches_expected_crs, EXPECTED_RES_M

YEARS = ("2010", "2015", "2018")
LABELS = {0: "Ej skogsmark", 1: "Produktiv skogsmark", 2: "Improduktiv skogsmark"}
VOLUME_BINS = [("0",0,0),("0-50",0,50),("50-100",50,100),("100-200",100,200),("200+",200,None)]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for y in YEARS:
        p.add_argument("--raster-"+y,type=Path,required=True)
    p.add_argument("--nmd",type=Path,required=True,help="Original 10m NMD2018 v1.1 productivity raster")
    p.add_argument("--volume-2010",type=Path,required=True)
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--output",type=Path,default=Path("metadata/nmd2018_nonforest_volume_diagnostic.json"))
    p.add_argument("--tile-size",type=int,default=256)
    args=p.parse_args()
    if not 16 <= args.tile_size <= 2048:
        p.error("tile-size must be between 16 and 2048")
    doc=json.loads(args.boundary.read_text(encoding="utf-8"))
    if doc.get("type")!="FeatureCollection" or len(doc.get("features",[]))!=1:
        raise ValueError("A single valid EPSG:4326 Lulea working boundary is required")
    geometry=shape(doc["features"][0]["geometry"])
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError("Invalid Lulea geometry")
    projected=geom_transform(
        Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,geometry)
    if projected.is_empty or not projected.is_valid:
        raise ValueError("Bad EPSG:3006 municipality geometry")
    step=25
    x0,y0,x1,y1=projected.bounds
    x0=math.floor(x0/step)*step
    y0=math.floor(y0/step)*step
    x1=math.ceil(x1/step)*step
    y1=math.ceil(y1/step)*step
    width=int(round((x1-x0)/step))
    height=int(round((y1-y0)/step))
    if width*height>40_000_000:
        raise ValueError("Unreasonable target grid")
    grid=Affine(step,0,x0,0,-step,y1)
    paths={y:getattr(args,"raster_"+y) for y in YEARS}
    counts={k:0 for k in LABELS}
    cross={(cls,name):{"cells":0,"sum":{y:0.0 for y in YEARS}} for cls in LABELS for name,_,_ in VOLUME_BINS}
    volume_missing_by_class={cls:0 for cls in LABELS}
    sums={k:{y:0.0 for y in YEARS} for k in LABELS}
    positive={k:{y:0 for y in YEARS} for k in LABELS}
    paired_cells=0
    nmd_no_data=0
    invalid_nmd=0
    nmd_source_info={}
    biomass_info={}
    with ExitStack() as stack:
        vrt={}
        for year,path in paths.items():
            src=stack.enter_context(rasterio.open(path))
            expected={ "2010":3021,"2015":3006,"2018":3006}[year]
            if not matches_expected_crs(src.crs, expected) or src.count!=1 or src.nodata is None:
                raise ValueError(f"{year} invalid source CRS, band count or NoData")
            if any(abs(abs(r)-EXPECTED_RES_M[year])>.05 for r in src.res):
                raise ValueError(f"{year} unverified resolution {src.res}")
            if src.scales[0]!=1 or src.offsets[0]!=0:
                raise ValueError(f"{year} unexpected scale/offset")
            biomass_info[year]={"path":str(path),"crs":str(src.crs),
                                 "resolution_m":list(src.res),"nodata":float(src.nodata)}
            vrt[year]=stack.enter_context(WarpedVRT(
                src,crs="EPSG:3006",transform=grid,width=width,height=height,
                resampling=Resampling.average,src_nodata=src.nodata,
                nodata=-9999.0,dtype="float32"))
        volume=stack.enter_context(rasterio.open(args.volume_2010))
        if not matches_expected_crs(volume.crs,3021) or volume.count!=1 or volume.nodata is None:
            raise ValueError("2010 volume clip has invalid source CRS, band count or NoData")
        if any(abs(abs(r)-25)>.05 for r in volume.res):
            raise ValueError("Unexpected 2010 volume native pixel resolution")
        vol_vrt=stack.enter_context(WarpedVRT(volume,crs="EPSG:3006",transform=grid,width=width,height=height,
            resampling=Resampling.average,src_nodata=volume.nodata,nodata=-9999.0,dtype="float32"))
        nmd=stack.enter_context(rasterio.open(args.nmd))
        if nmd.crs is None or nmd.crs.to_epsg()!=3006 or nmd.count!=1:
            raise ValueError("Expected official NMD2018 v1.1 single-band EPSG:3006 raster")
        if any(abs(abs(r)-10)>.01 for r in nmd.res):
            raise ValueError("Expected 10m NMD2018 source raster")
        if nmd.nodata in LABELS:
            raise ValueError("NMD NoData conflicts with class code")
        if nmd.bounds.right < x0 or nmd.bounds.left > x1 or nmd.bounds.top < y0 or nmd.bounds.bottom > y1:
            raise ValueError("NMD outside the target extent")
        nmd_source_info={"path":str(args.nmd),"crs":str(nmd.crs),
                         "resolution_m":list(nmd.res),"nodata":nmd.nodata}
        # The whole NMD grid is resampled categorically to the 25m analysis grid;
        # zeros remain true class zeros, even if source NoData is unspecified.
        nv=stack.enter_context(WarpedVRT(
            nmd,crs="EPSG:3006",transform=grid,width=width,height=height,
            resampling=Resampling.nearest,src_nodata=nmd.nodata,
            nodata=255,dtype="uint8"))
        for row in range(0,height,args.tile_size):
            for col in range(0,width,args.tile_size):
                win=Window(col,row,min(args.tile_size,width-col),
                           min(args.tile_size,height-row))
                inside=geometry_mask([mapping(projected)],
                    out_shape=(int(win.height),int(win.width)),
                    transform=rasterio.windows.transform(win,grid),
                    invert=True,all_touched=False)
                if not inside.any():
                    continue
                arrays={}
                mask=inside.copy()
                for year in YEARS:
                    data=vrt[year].read(1,window=win,masked=True)
                    arr=np.ma.asarray(data,dtype="float64").filled(np.nan)
                    arrays[year]=arr
                    mask &= np.isfinite(arr) & (arr>=0)
                count=int(mask.sum())
                if count==0:
                    continue
                paired_cells+=count
                vol=vol_vrt.read(1,window=win,masked=True)
                volvalues=np.ma.asarray(vol,dtype="float64").filled(np.nan)
                goodvolume=np.isfinite(volvalues)&(volvalues>=0)
                nm=nv.read(1,window=win,masked=True)
                vals=nm.data
                available=mask & (~np.ma.getmaskarray(nm)) & (vals!=255)
                nmd_no_data+=count-int(available.sum())
                classified=np.zeros_like(available,dtype=bool)
                for cls in LABELS:
                    select=available & (vals==cls)
                    classified |= select
                    n=int(select.sum())
                    counts[cls]+=n
                    volume_missing_by_class[cls]+=int((select & ~goodvolume).sum())
                    for binname,low,high in VOLUME_BINS:
                        if high==0:
                            bucket=select & goodvolume & (volvalues==0)
                        elif high is None:
                            bucket=select & goodvolume & (volvalues>=low)
                        else:
                            bucket=select & goodvolume & (volvalues>low if low==0 else volvalues>=low) & (volvalues<high)
                        entry=cross[(cls,binname)]
                        entry["cells"]+=int(bucket.sum())
                        for year in YEARS:
                            entry["sum"][year]+=float(arrays[year][bucket].sum(dtype="float64"))
                    for year in YEARS:
                        x=arrays[year][select]
                        sums[cls][year]+=float(x.sum(dtype="float64"))
                        positive[cls][year]+=int(np.count_nonzero(x>0))
                invalid_nmd+=int((available & ~classified).sum())
    total=sum(counts.values())
    if total<10000:
        raise ValueError(f"Insufficient classified common cells: {total}")
    if total+nmd_no_data+invalid_nmd!=paired_cells:
        raise AssertionError("NMD partition does not match paired-biomass population")
    integrated={y:sum(sums[k][y] for k in LABELS) for y in YEARS}
    rows=[]
    for cls,label in LABELS.items():
        n=counts[cls]
        means={y:(sums[cls][y]/n if n else None) for y in YEARS}
        rows.append({
            "class":cls,"label":label,"cells":n,"area_ha":n*.0625,
            "share_of_classified_area":n/total,
            "raw_biomass_means":means,
            "positive_biomass_fraction":{y:(positive[cls][y]/n if n else None) for y in YEARS},
            "raw_difference_2010_minus_2015":means["2010"]-means["2015"] if n else None,
            "raw_difference_2010_minus_2018":means["2010"]-means["2018"] if n else None,
            "share_of_total_raw_difference_2010_minus_2015":(
                (sums[cls]["2010"]-sums[cls]["2015"])/(integrated["2010"]-integrated["2015"])
                if integrated["2010"]!=integrated["2015"] else None),
            "share_of_total_raw_difference_2010_minus_2018":(
                (sums[cls]["2010"]-sums[cls]["2018"])/(integrated["2010"]-integrated["2018"])
                if integrated["2010"]!=integrated["2018"] else None)
        })
    cross_rows=[]
    for cls,label in LABELS.items():
        for binname,_,_ in VOLUME_BINS:
            entry=cross[(cls,binname)]
            n=entry["cells"]
            cross_rows.append({"class":cls,"class_label":label,"volume_2010_bin":binname,
              "cells":n,"area_ha":n*.0625,
              "biomass_mean_raw":{y:(entry["sum"][y]/n if n else None) for y in YEARS},
              "share_of_all_2010_minus_2018":(entry["sum"]["2010"]-entry["sum"]["2018"])/(integrated["2010"]-integrated["2018"]) if integrated["2010"]!=integrated["2018"] else None})
    if any(sum(cross[(cls,b)]["cells"] for b,_,_ in VOLUME_BINS)+volume_missing_by_class[cls]!=counts[cls] for cls in LABELS):
        raise ValueError("Volume bins do not partition NMD class")
    out={
        "status":"DESCRIPTIVE_NMD2018_2010_VOLUME_CROSS_NOT_HARMONIZED",
        "volume_2010_source":{"path":str(args.volume_2010),"crs":str(volume.crs),"nodata":volume.nodata},
        "volume_2010_bin_by_nmd":cross_rows,
        "volume_missing_by_nmd_class":volume_missing_by_class,
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "main_population_class":1,
        "nmd_version":"NMD2018 produktivitet v1.1 (fixed across comparisons)",
        "source_url":"https://geodata.naturvardsverket.se/nedladdning/marktacke/NMD2018/NMD_Produktivitet_v1_1.zip",
        "nmd_source":nmd_source_info,"biomass_sources":biomass_info,
        "analysis_crs":"EPSG:3006","analysis_resolution_m":25,
        "area_per_cell_ha":.0625,
        "paired_biomass_cells_before_nmd":paired_cells,
        "nmd_nodata_common_cells":nmd_no_data,
        "nmd_unknown_class_common_cells":invalid_nmd,
        "classified_common_cells":total,"classified_common_area_ha":total*.0625,
        "classes":rows,
        "classification_sum_check":sum(x["cells"] for x in rows)==total,
        "limitations":[
            "NMD2018 is fixed for all years, NOT a historical observation of 2010 or 2015",
            "NMD2018 may use earlier SLU forest map inputs: not independent",
            "Class 0 includes land outside forestry and must not be interpreted as forest productivity",
            "The Lulea working municipal geometry is not an independently verified legal boundary",
            "Biomass products differ in components and methodology; raw values are not harmonized tonnes",
            "Class-specific 2010-2015 differences are descriptive and do not establish harvesting or growth causes",
            "Pixel counts and hectares are from EPSG:3006 25m analysis grid, NEVER EPSG:3857 preview"
        ]
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("NMD classes, cells:",counts,"paired:",paired_cells,
          "NMD missing:",nmd_no_data,"unknown:",invalid_nmd)
    print("Main population:",next(x for x in rows if x["class"]==1))
    print("Cross-class 2010-volume:",json.dumps(cross_rows,ensure_ascii=False))

if __name__=="__main__":
    main()
