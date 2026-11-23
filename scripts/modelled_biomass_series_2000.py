#!/usr/bin/env python3
"""Exploratory biomass 2000-2018: volume-calibrated 2000/05, observed 2010/15/18.

One common 25 m EPSG:3006 grid and identical valid support across FIVE
rasters (volumes 2000/05/10 and biomass 2010/15/18). 2010 calibration is
the ratio of area-weighted sums, NOT mean of per-cell quotients. Physical
biomass components differ across source generations; never label as a
verified chronological biomass change, CO2 or carbon stock.
"""
from __future__ import annotations
import argparse,json,math
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from pyproj import Transformer
from shapely.geometry import shape,mapping
from shapely.ops import transform as transform_shape
from fetch_and_compare_biomass_native import matches_expected_crs
from analyze_historic_volume import validate_archive
from verify_biomass_release import run as validate_biomass

SOURCE={
 "vol_2000":("volume", "2000",3021),
 "vol_2005":("volume", "2005",3021),
 "vol_2010":("volume", "2010",3021),
 "bio_2010":("biomass", "2010",3021),
 "bio_2015":("biomass", "2015",3006),
 "bio_2018":("biomass", "2018",3006),
}
def run(a):
    boundary_doc=json.loads(a.boundary.read_text(encoding="utf-8"))
    if boundary_doc.get("type")!="FeatureCollection" or len(boundary_doc.get("features",[]))!=1:
        raise ValueError("One EPSG:4326 polygon feature required")
    polygon=shape(boundary_doc["features"][0]["geometry"])
    if polygon.is_empty or not polygon.is_valid:raise ValueError("Invalid project polygon")
    validate_archive(a.volume_dir,a.boundary)
    validate_biomass(argparse.Namespace(directory=a.biomass_dir,output=a.qa_output))
    target_polygon=transform_shape(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,polygon)
    left,bottom,right,top=target_polygon.bounds
    size=25.0
    left=math.floor(left/size)*size;bottom=math.floor(bottom/size)*size
    right=math.ceil(right/size)*size;top=math.ceil(top/size)*size
    width=round((right-left)/size);height=round((top-bottom)/size)
    if width*height>40_000_000:raise ValueError("Unreasonable project extent")
    transform=Affine(size,0,left,0,-size,top)
    sums={name:0.0 for name in SOURCE}
    zeros={name:0 for name in SOURCE}
    count=0
    with ExitStack() as stack:
        vrts={}
        for name,(kind,year,epsg) in SOURCE.items():
            if kind=="volume": file=a.volume_dir/f"lulea_total_volume_{year}_source_crs_clip.tif"
            else:file=a.biomass_dir/f"lulea_biomass_{year}_source_crs_clip.tif"
            src=stack.enter_context(rasterio.open(file))
            if not matches_expected_crs(src.crs,epsg) or src.count!=1 or src.nodata!=-9999:
                raise ValueError("CRS/band/NoData mismatch for "+name)
            vrts[name]=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=transform,
                              width=width,height=height,src_nodata=src.nodata,nodata=-9999,
                              resampling=Resampling.average,dtype="float32"))
        for r in range(0,height,256):
            for c in range(0,width,256):
                win=Window(c,r,min(256,width-c),min(256,height-r))
                tf=rasterio.windows.transform(win,transform)
                inside=geometry_mask([mapping(target_polygon)],out_shape=(int(win.height),int(win.width)),
                                     transform=tf,invert=True,all_touched=False)
                if not np.any(inside):continue
                arrays={name:np.ma.asarray(v.read(1,window=win,masked=True),
                                             dtype="float64").filled(np.nan) for name,v in vrts.items()}
                valid=inside
                for values in arrays.values():valid=valid & np.isfinite(values) & (values>=0)
                n=int(valid.sum())
                if not n:continue
                count+=n
                for name,values in arrays.items():
                    subset=values[valid]
                    sums[name]+=float(subset.sum(dtype="float64"))
                    zeros[name]+=int(np.count_nonzero(subset==0))
    if not count or sums["vol_2010"]<=0:raise ValueError("No five-way common support or zero calibration volume")
    factor=sums["bio_2010"]/sums["vol_2010"]
    if not math.isfinite(factor) or factor<=0:raise ValueError("Invalid positive 2010 biomass-volume ratio")
    rows=[]
    for year in (2000,2005,2010,2015,2018):
        if year<2010:
            estimated=sums[f"vol_{year}"]*factor/count
            status="MODELLED_volume_times_2010_aggregate_ratio"
            source=f"SLU total wood volume {year}; scaled with joint-area 2010 ratio"
            low,high=estimated*0.8,estimated*1.2
        else:
            estimated=sums[f"bio_{year}"]/count
            status="OBSERVED_raster_raw_mean_not_harmonized_between_products"
            source=f"Archived SLU/SGD biomass product {year}"
            low=high=None
        rows.append({"year":year,"raw_mean_on_common_support":estimated,
                     "status":status,"source":source,
                     "scenario_low_minus_20pct":low,"scenario_high_plus_20pct":high})
    output={
      "created_utc":datetime.now(timezone.utc).isoformat(),
      "status":"EXPLORATORY_MODEL_NOT_A_VALIDATED_BIOMASS_TIMESERIES",
      "comparison_crs":"EPSG:3006","target_cell_m":25,
      "common_valid_cells":count,"common_valid_area_ha":count*0.0625,
      "calibration_year":2010,
      "calibration_formula":"sum(raw_2010_biomass on joint cells) / sum(raw_2010_total_volume on joint cells)",
      "calibration_factor_raw_biomass_per_raw_volume":factor,
      "scenario_description":"The +/-20% bands are arbitrary sensitivity scenarios for 2000/2005, NOT confidence intervals",
      "comparison_basis":"Five timestamps on six raster layers, same 25 m cells with valid pixels in all products.",
      "years":rows,
      "zero_share_by_source":{k:zeros[k]/count for k in SOURCE},
      "limitations":[
       "2010 biomass calibrated by same-model 2010 volume and is not independent validation",
       "Biomass definitions may differ: 2010 includes above/belowground per kNN technical source; 2015 aboveground",
       "The 2015/2018 values are observed raster raw values, not corrected for product methodological changes",
       "2000 and 2005 are model estimates, not original biomass observations",
       "No verified forest mask, species or age/site-index adjustment yet",
       "Do NOT infer biomass stock changes, growth rates, carbon or CO2 from this exploratory series",
       "Source epochs are map labels; actual observation times depend on imagery and lidar collection"
      ]
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(output,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--volume-dir",type=Path,default=Path("release-volume"))
    p.add_argument("--biomass-dir",type=Path,default=Path("release-biomass"))
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--qa-output",type=Path,default=Path("metadata/biomass_release_validation.json"))
    p.add_argument("--output",type=Path,default=Path("metadata/modelled_biomass_series_2000_2018.json"))
    run(p.parse_args())
