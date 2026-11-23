#!/usr/bin/env python3
"""Compare 2010/2015/2018 original biomass rasters on one metric area grid.

The analysis uses *native* GeoTIFF source rasters, not EPSG:3857 previews.
An aligned EPSG:3006 25 m grid makes all three products represent the same
625 m2 cells. Density rasters are resampled with average, then multiplied
by 0.0625 ha. NoData stays missing. A municipal boundary is centre-masked.
Results are descriptive until native physical units and biomass components
are independently confirmed. No source TIFF or existing website total changes.
"""
from __future__ import annotations
import argparse
import json
import math
import re
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
from shapely.geometry import mapping, shape
from shapely.ops import transform as shape_transform
from pyproj import Transformer, CRS as PyprojCRS

ROOT = Path(__file__).resolve().parents[1]
YEARS = ("2010", "2015", "2018")
EXPECTED_RES_M = {"2010":25.0,"2015":12.5,"2018":10.0}

def matches_expected_crs(source_crs, expected_epsg):
    """Check expected EPSG, also recognizing the top-level authority of legacy WKT1.

    WKT1 exported by some older SLU GeoTIFFs carries AUTHORITY["EPSG","3021"]
    at the outermost PROJCS level, although PROJ/pyproj may not report equality
    with the modern EPSG database definition. Never accept an unknown CRS.
    """
    if source_crs is None:
        return False
    try:
        if source_crs.to_epsg() == expected_epsg:
            return True
        wkt = source_crs.to_wkt()
        if PyprojCRS.from_user_input(wkt).equals(
            PyprojCRS.from_epsg(expected_epsg), ignore_axis_order=True
        ):
            return True
        # Last AUTHORITY/ID, immediately before the final CRS bracket,
        # identifies the outer PROJCS rather than a nested datum/ellipsoid.
        match = re.search(
            r'(?:AUTHORITY|ID)\s*\[\s*"EPSG"\s*,\s*"?([0-9]+)"?\s*\]\s*\]\s*
def run(args):
    boundary_doc=json.loads(args.boundary.read_text(encoding="utf-8"))
    if boundary_doc.get("type") != "FeatureCollection":
        raise ValueError("Boundary must be GeoJSON FeatureCollection with verified EPSG:4326 coordinates")
    geometries=[shape(f["geometry"]) for f in boundary_doc["features"]]
    if len(geometries) != 1 or geometries[0].is_empty or not geometries[0].is_valid:
        raise ValueError("One valid Lulea polygon or multipolygon is required")
    boundary=shape_transform(
        Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,
        geometries[0])
    if boundary.is_empty or not boundary.is_valid:
        raise ValueError("Transformed boundary invalid")
    step=float(args.grid_resolution)
    if step<=0 or not math.isfinite(step):
        raise ValueError("Invalid target resolution")
    left,bottom,right,top=boundary.bounds
    left=math.floor(left/step)*step
    right=math.ceil(right/step)*step
    bottom=math.floor(bottom/step)*step
    top=math.ceil(top/step)*step
    width=round((right-left)/step)
    height=round((top-bottom)/step)
    if width*height>100_000_000:
        raise ValueError("Target grid unreasonably large")
    target=Affine(step,0,left,0,-step,top)
    ha=step*step/10_000
    paths={"2010":args.raster_2010,"2015":args.raster_2015,"2018":args.raster_2018}
    selected=paths.keys()
    if args.units_confirmed and not args.unit_evidence:
        raise ValueError("--units-confirmed requires --unit-evidence with explicit source references")
    if args.units_confirmed and not args.component_evidence:
        raise ValueError("--units-confirmed requires --component-evidence documenting comparability")
    counts_common={k:0 for k in YEARS}
    sums_common={k:0.0 for k in YEARS}
    counts_own={k:0 for k in YEARS}
    sums_own={k:0.0 for k in YEARS}
    source_info={}
    with ExitStack() as stack:
        vrts={}
        for year in selected:
            src=stack.enter_context(rasterio.open(paths[year]))
            if src.count<1 or not src.crs or not matches_expected_crs(src.crs, {"2010":3021,"2015":3006,"2018":3006}[year]):
                raise ValueError(f"{year}: unverified source raster band/CRS: {src.crs}")
            rx,ry=map(abs,src.res)
            expected=EXPECTED_RES_M[year]
            if not math.isclose(rx,expected,abs_tol=0.05) or not math.isclose(ry,expected,abs_tol=0.05):
                raise ValueError(f"{year}: native resolution {src.res}, expected {expected} m; verify product before analysis")
            if src.scales[0]!=1 or src.offsets[0]!=0:
                raise ValueError(f"{year}: nonidentity band scale/offset needs separate audited unit treatment")
            if src.nodata is None:
                raise ValueError(f"{year}: source NoData unspecified; set it explicitly and document before comparing")
            source_info[year]={"path":str(paths[year]),"crs":str(src.crs),
                               "resolution_m":[rx,ry],"nodata":float(src.nodata),
                               "source_band_scale":src.scales[0],"source_band_offset":src.offsets[0]}
            vrts[year]=stack.enter_context(WarpedVRT(
                src,crs="EPSG:3006",transform=target,width=width,height=height,
                src_nodata=src.nodata,nodata=-9999.0,resampling=Resampling.average,
                dtype="float32"))
        for r0 in range(0,height,args.tile_size):
            for c0 in range(0,width,args.tile_size):
                h=min(args.tile_size,height-r0)
                w=min(args.tile_size,width-c0)
                window=Window(c0,r0,w,h)
                tf=rasterio.windows.transform(window,target)
                inside=geometry_mask([mapping(boundary)],out_shape=(h,w),
                                     transform=tf,invert=True,all_touched=False)
                if not inside.any():
                    continue
                values={}
                valid={}
                for year in YEARS:
                    data=vrts[year].read(1,window=window,masked=True)
                    arr=np.asarray(data.filled(np.nan),dtype="float64")
                    good=inside&np.isfinite(arr)&(arr>=0)
                    if np.any(inside&np.isfinite(arr)&(arr<0)):
                        # Nonnegative densities are expected; negative true values may
                        # indicate unknown scale/nodata conventions.
                        raise ValueError(f"{year}: negative values inside municipality")
                    values[year]=arr
                    valid[year]=good
                    counts_own[year]+=int(good.sum())
                    sums_own[year]+=float(np.sum(arr[good],dtype="float64"))*ha
                common=valid["2010"]&valid["2015"]&valid["2018"]
                for year in YEARS:
                    counts_common[year]+=int(common.sum())
                    sums_common[year]+=float(np.sum(values[year][common],dtype="float64"))*ha
    common_n=counts_common["2010"]
    if not common_n:
        raise ValueError("No common valid original-raster grid cells")
    mass_label="tonnes_dry_biomass_conditional_on_confirmed_units" if args.units_confirmed else "raw_density_times_hectares_UNVERIFIED_units"
    result={
      "schema_version":1,"calculated_utc":datetime.now(timezone.utc).isoformat(),
      "source_rasters":source_info,"target_crs":"EPSG:3006",
      "target_resolution_m":step,"target_cell_area_ha":ha,
      "target_grid_width":width,"target_grid_height":height,
      "boundary_status":"Lulea project working geometry, not verified official municipal boundary",
      "aggregation":"Area integral of EPSG:3006 averaged densities, masked by centre inclusion",
      "resampling":"average density, never sum of source raster density cells",
      "common_valid_cells":common_n,"common_valid_area_ha":common_n*ha,
      "per_year":{
        y:{"mean_density_common_raw":sums_common[y]/(common_n*ha),
           "integrated_common":sums_common[y],
           "valid_own_area_ha":counts_own[y]*ha,
           "integrated_own_coverage":sums_own[y],
           "valid_own_cells":counts_own[y]} for y in YEARS},
      "integral_unit":mass_label,
      "unit_evidence":args.unit_evidence if args.units_confirmed else None,
      "component_evidence":args.component_evidence if args.units_confirmed else None,
      "tonnes_C":None,
      "note":"Different source resolutions have been harmonized by area-aware average density; this does not prove equivalence of biomass components, model methods, epochs or native units. Only the common footprint is a same-area comparison. No missing northern cells have been invented.",
      "original_rasters_modified":False
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Common valid hectares:",round(common_n*ha,2))
    for year in YEARS:
        v=result["per_year"][year]
        print(year,"mean raw density:",round(v["mean_density_common_raw"],3),
              "common raw density x ha:",round(v["integrated_common"],3))
    print("Unit:",mass_label,"; original rasters unchanged")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raster-2010",type=Path,required=True)
    p.add_argument("--raster-2015",type=Path,required=True)
    p.add_argument("--raster-2018",type=Path,required=True)
    p.add_argument("--boundary",type=Path,default=ROOT/"docs/data/lulea_boundary.geojson")
    p.add_argument("--output",type=Path,default=ROOT/"metadata/biomass_native_area_comparison.json")
    p.add_argument("--grid-resolution",type=float,default=25.0)
    p.add_argument("--tile-size",type=int,default=256)
    p.add_argument("--units-confirmed",action="store_true",help="Require source references for all three rasters being comparable in tonnes dry/ha")
    p.add_argument("--unit-evidence",default=None)
    p.add_argument("--component-evidence",default=None)
    a=p.parse_args()
    if a.tile_size<16 or a.tile_size>2048:p.error("tile-size must be 16..2048")
    run(a)
if __name__=="__main__":main()
,
            wkt, re.IGNORECASE,
        )
        return bool(match and int(match.group(1)) == expected_epsg)
    except (ValueError, TypeError, RuntimeError):
        return False

def run(args):
    boundary_doc=json.loads(args.boundary.read_text(encoding="utf-8"))
    if boundary_doc.get("type") != "FeatureCollection":
        raise ValueError("Boundary must be GeoJSON FeatureCollection with verified EPSG:4326 coordinates")
    geometries=[shape(f["geometry"]) for f in boundary_doc["features"]]
    if len(geometries) != 1 or geometries[0].is_empty or not geometries[0].is_valid:
        raise ValueError("One valid Lulea polygon or multipolygon is required")
    boundary=shape_transform(
        Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,
        geometries[0])
    if boundary.is_empty or not boundary.is_valid:
        raise ValueError("Transformed boundary invalid")
    step=float(args.grid_resolution)
    if step<=0 or not math.isfinite(step):
        raise ValueError("Invalid target resolution")
    left,bottom,right,top=boundary.bounds
    left=math.floor(left/step)*step
    right=math.ceil(right/step)*step
    bottom=math.floor(bottom/step)*step
    top=math.ceil(top/step)*step
    width=round((right-left)/step)
    height=round((top-bottom)/step)
    if width*height>100_000_000:
        raise ValueError("Target grid unreasonably large")
    target=Affine(step,0,left,0,-step,top)
    ha=step*step/10_000
    paths={"2010":args.raster_2010,"2015":args.raster_2015,"2018":args.raster_2018}
    selected=paths.keys()
    if args.units_confirmed and not args.unit_evidence:
        raise ValueError("--units-confirmed requires --unit-evidence with explicit source references")
    if args.units_confirmed and not args.component_evidence:
        raise ValueError("--units-confirmed requires --component-evidence documenting comparability")
    counts_common={k:0 for k in YEARS}
    sums_common={k:0.0 for k in YEARS}
    counts_own={k:0 for k in YEARS}
    sums_own={k:0.0 for k in YEARS}
    source_info={}
    with ExitStack() as stack:
        vrts={}
        for year in selected:
            src=stack.enter_context(rasterio.open(paths[year]))
            if src.count<1 or not src.crs or not matches_expected_crs(src.crs, {"2010":3021,"2015":3006,"2018":3006}[year]):
                raise ValueError(f"{year}: unverified source raster band/CRS: {src.crs}")
            rx,ry=map(abs,src.res)
            expected=EXPECTED_RES_M[year]
            if not math.isclose(rx,expected,abs_tol=0.05) or not math.isclose(ry,expected,abs_tol=0.05):
                raise ValueError(f"{year}: native resolution {src.res}, expected {expected} m; verify product before analysis")
            if src.scales[0]!=1 or src.offsets[0]!=0:
                raise ValueError(f"{year}: nonidentity band scale/offset needs separate audited unit treatment")
            if src.nodata is None:
                raise ValueError(f"{year}: source NoData unspecified; set it explicitly and document before comparing")
            source_info[year]={"path":str(paths[year]),"crs":str(src.crs),
                               "resolution_m":[rx,ry],"nodata":float(src.nodata),
                               "source_band_scale":src.scales[0],"source_band_offset":src.offsets[0]}
            vrts[year]=stack.enter_context(WarpedVRT(
                src,crs="EPSG:3006",transform=target,width=width,height=height,
                src_nodata=src.nodata,nodata=-9999.0,resampling=Resampling.average,
                dtype="float32"))
        for r0 in range(0,height,args.tile_size):
            for c0 in range(0,width,args.tile_size):
                h=min(args.tile_size,height-r0)
                w=min(args.tile_size,width-c0)
                window=Window(c0,r0,w,h)
                tf=rasterio.windows.transform(window,target)
                inside=geometry_mask([mapping(boundary)],out_shape=(h,w),
                                     transform=tf,invert=True,all_touched=False)
                if not inside.any():
                    continue
                values={}
                valid={}
                for year in YEARS:
                    data=vrts[year].read(1,window=window,masked=True)
                    arr=np.asarray(data.filled(np.nan),dtype="float64")
                    good=inside&np.isfinite(arr)&(arr>=0)
                    if np.any(inside&np.isfinite(arr)&(arr<0)):
                        # Nonnegative densities are expected; negative true values may
                        # indicate unknown scale/nodata conventions.
                        raise ValueError(f"{year}: negative values inside municipality")
                    values[year]=arr
                    valid[year]=good
                    counts_own[year]+=int(good.sum())
                    sums_own[year]+=float(np.sum(arr[good],dtype="float64"))*ha
                common=valid["2010"]&valid["2015"]&valid["2018"]
                for year in YEARS:
                    counts_common[year]+=int(common.sum())
                    sums_common[year]+=float(np.sum(values[year][common],dtype="float64"))*ha
    common_n=counts_common["2010"]
    if not common_n:
        raise ValueError("No common valid original-raster grid cells")
    mass_label="tonnes_dry_biomass_conditional_on_confirmed_units" if args.units_confirmed else "raw_density_times_hectares_UNVERIFIED_units"
    result={
      "schema_version":1,"calculated_utc":datetime.now(timezone.utc).isoformat(),
      "source_rasters":source_info,"target_crs":"EPSG:3006",
      "target_resolution_m":step,"target_cell_area_ha":ha,
      "target_grid_width":width,"target_grid_height":height,
      "boundary_status":"Lulea project working geometry, not verified official municipal boundary",
      "aggregation":"Area integral of EPSG:3006 averaged densities, masked by centre inclusion",
      "resampling":"average density, never sum of source raster density cells",
      "common_valid_cells":common_n,"common_valid_area_ha":common_n*ha,
      "per_year":{
        y:{"mean_density_common_raw":sums_common[y]/(common_n*ha),
           "integrated_common":sums_common[y],
           "valid_own_area_ha":counts_own[y]*ha,
           "integrated_own_coverage":sums_own[y],
           "valid_own_cells":counts_own[y]} for y in YEARS},
      "integral_unit":mass_label,
      "unit_evidence":args.unit_evidence if args.units_confirmed else None,
      "component_evidence":args.component_evidence if args.units_confirmed else None,
      "tonnes_C":None,
      "note":"Different source resolutions have been harmonized by area-aware average density; this does not prove equivalence of biomass components, model methods, epochs or native units. Only the common footprint is a same-area comparison. No missing northern cells have been invented.",
      "original_rasters_modified":False
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Common valid hectares:",round(common_n*ha,2))
    for year in YEARS:
        v=result["per_year"][year]
        print(year,"mean raw density:",round(v["mean_density_common_raw"],3),
              "common raw density x ha:",round(v["integrated_common"],3))
    print("Unit:",mass_label,"; original rasters unchanged")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raster-2010",type=Path,required=True)
    p.add_argument("--raster-2015",type=Path,required=True)
    p.add_argument("--raster-2018",type=Path,required=True)
    p.add_argument("--boundary",type=Path,default=ROOT/"docs/data/lulea_boundary.geojson")
    p.add_argument("--output",type=Path,default=ROOT/"metadata/biomass_native_area_comparison.json")
    p.add_argument("--grid-resolution",type=float,default=25.0)
    p.add_argument("--tile-size",type=int,default=256)
    p.add_argument("--units-confirmed",action="store_true",help="Require source references for all three rasters being comparable in tonnes dry/ha")
    p.add_argument("--unit-evidence",default=None)
    p.add_argument("--component-evidence",default=None)
    a=p.parse_args()
    if a.tile_size<16 or a.tile_size>2048:p.error("tile-size must be 16..2048")
    run(a)
if __name__=="__main__":main()
