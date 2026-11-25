#!/usr/bin/env python3
"""Native-grid 2010 SLU data-mask sensitivity to NMD2018 water cover.

The 2010 biomass and volume pixels are NEVER resampled in this analysis.
Original 10m NMD2018 categorical water/validity masks are reprojected by
area average to the genuine 25m EPSG:3021 source pixel grid, window by window.
NMD2018 water is explicitly not asserted to be historical 2010 water.
"""
from __future__ import annotations

import argparse
import base64
import zlib
import json
import math
from collections import defaultdict
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds
from rasterio.warp import reproject, transform_bounds
from scipy.ndimage import binary_dilation
from shapely.geometry import shape, mapping
from shapely.ops import transform as reproject_geom
from fetch_and_compare_biomass_native import matches_expected_crs

WATER={61,62}
BINS=("0 %",">0-25 %",">25-50 %",">50-75 %",">75-<100 %","100 %")
GROUPS=("4 sidogrannar med mark","Endast diagonal markgranne","Ingen mark bland 8 grannar")

def bin_masks(f):
    return (
        f<=1.e-5,
        (f>1.e-5)&(f<=.25),
        (f>.25)&(f<=.50),
        (f>.50)&(f<=.75),
        (f>.75)&(f<.999),
        f>=.999
    )

def render_native_fraction(nmd, native_transform, width, height, tile=256):
    """Project native 10m *binary* NMD water and source-validity to native EPSG:3021.

    Per-window source bounds are transformed using their actual CRS; full
    destination raster grids are calculated, never inferred from transformed
    bounding boxes without raster reprojection.
    """
    water=np.zeros((height,width),dtype=np.float32)
    coverage=np.zeros_like(water)
    source_epsg="EPSG:3006"
    target_epsg="EPSG:3021"
    for y in range(0,height,tile):
        for x in range(0,width,tile):
            w=Window(x,y,min(tile,width-x),min(tile,height-y))
            dest_bounds=rasterio.windows.bounds(w,native_transform)
            source_bounds=transform_bounds(target_epsg,source_epsg,*dest_bounds,densify_pts=21)
            win=from_bounds(*source_bounds,transform=nmd.transform)
            x0=math.floor(win.col_off)-4
            y0=math.floor(win.row_off)-4
            x1=math.ceil(win.col_off+win.width)+4
            y1=math.ceil(win.row_off+win.height)+4
            source_w=Window(x0,y0,x1-x0,y1-y0)
            src=nmd.read(1,window=source_w,boundless=True,fill_value=nmd.nodata)
            native_valid=(src!=nmd.nodata).astype(np.float32)
            native_water=np.isin(src,list(WATER)).astype(np.float32)
            s_transform=rasterio.windows.transform(source_w,nmd.transform)
            d_transform=rasterio.windows.transform(w,native_transform)
            dims=(int(w.height),int(w.width))
            out_water=np.zeros(dims,dtype=np.float32)
            out_valid=np.zeros(dims,dtype=np.float32)
            for v,d in ((native_water,out_water),(native_valid,out_valid)):
                reproject(source=v,destination=d,
                    src_transform=s_transform,src_crs=nmd.crs,
                    dst_transform=d_transform,dst_crs=target_epsg,
                    resampling=Resampling.average,
                    init_dest_nodata=True)
            water[y:y+dims[0],x:x+dims[1]]=out_water
            coverage[y:y+dims[0],x:x+dims[1]]=out_valid
    return water,coverage

def empty_stats():
    return {"nmd_covered_cells":0,"biomass_valid":0,"volume_valid":0,
            "both_2010_valid":0,"biomass_zero":0,"volume_zero":0,
            "biomass_sum_valid":0.,"volume_sum_valid":0.}

def push_stats(stats,selection,b,v,b_valid,v_valid):
    n=int(selection.sum())
    if not n:return
    stats["nmd_covered_cells"]+=n
    vb=selection & b_valid
    vv=selection & v_valid
    stats["biomass_valid"]+=int(vb.sum())
    stats["volume_valid"]+=int(vv.sum())
    stats["both_2010_valid"]+=int((vb&vv).sum())
    stats["biomass_zero"]+=int((vb&(b==0)).sum())
    stats["volume_zero"]+=int((vv&(v==0)).sum())
    stats["biomass_sum_valid"]+=float(b[vb].sum(dtype=np.float64))
    stats["volume_sum_valid"]+=float(v[vv].sum(dtype=np.float64))

def describe(d):
    n=d["nmd_covered_cells"]
    nb=d["biomass_valid"]
    nv=d["volume_valid"]
    return {"cells":n,"area_ha":n*.0625,
      "biomass_2010_valid_cells":nb,
      "volume_2010_valid_cells":nv,
      "both_2010_valid_cells":d["both_2010_valid"],
      "biomass_2010_coverage_pct":100*nb/n if n else None,
      "volume_2010_coverage_pct":100*nv/n if n else None,
      "mean_biomass_2010_on_valid":d["biomass_sum_valid"]/nb if nb else None,
      "mean_volume_2010_on_valid":d["volume_sum_valid"]/nv if nv else None,
      "valid_biomass_zero_cells":d["biomass_zero"],
      "valid_volume_zero_cells":d["volume_zero"]}

def main(args):
    obj=json.loads(args.boundary.read_text(encoding="utf-8"))
    if obj.get("type")!="FeatureCollection" or len(obj.get("features",[]))!=1:
        raise ValueError("Expected municipality boundary in one GeoJSON EPSG:4326 feature")
    boundary=shape(obj["features"][0]["geometry"])
    if boundary.is_empty or not boundary.is_valid:
        raise ValueError("Invalid municipality boundary")
    polygon=reproject_geom(Transformer.from_crs("EPSG:4326","EPSG:3021",always_xy=True).transform,boundary)
    with ExitStack() as stack:
        b=stack.enter_context(rasterio.open(args.biomass_2010))
        v=stack.enter_context(rasterio.open(args.volume_2010))
        nmd=stack.enter_context(rasterio.open(args.nmd))
        for name,src,code,pix in (
           ("biomass_2010",b,3021,25),
           ("volume_2010",v,3021,25),
           ("nmd2018",nmd,3006,10)):
            if src.crs is None or not matches_expected_crs(src.crs,code):
                raise ValueError(f"{name}: source EPSG mismatch or missing CRS")
            if src.count!=1 or src.nodata is None or any(abs(abs(r)-pix)>.1 for r in src.res):
                raise ValueError(f"{name}: native resolution/band/nodata mismatch")
        if b.width!=v.width or b.height!=v.height or b.transform!=v.transform:
            raise ValueError("2010 biomass and volume do not share exact native grid; do not silently reproject one to other")
        source_metadata={
            "biomass_2010":{"epsg":3021,"resolution_m":list(b.res),"nodata":str(b.nodata),"mask_flags":[f.name for f in b.mask_flag_enums[0]]},
            "volume_2010":{"epsg":3021,"resolution_m":list(v.res),"nodata":str(v.nodata),"mask_flags":[f.name for f in v.mask_flag_enums[0]]},
            "nmd2018":{"epsg":3006,"resolution_m":list(nmd.res),"nodata":str(nmd.nodata),"mask_flags":[f.name for f in nmd.mask_flag_enums[0]]}
        }
        if b.width*b.height>30000000:raise ValueError("Unexpectedly large source raster")
        print("Projecting original NMD2018 water/coverage masks to native EPSG:3021 pixels",flush=True)
        water,coverage=render_native_fraction(nmd,b.transform,b.width,b.height)
        # Native NMD 10m may have NoData or only partial coverage of 2010 pixels.
        # Exclude these pixels from all water-fraction denominators.
        enough=coverage>=.999
        # 2018 category is NOT a validated historical 2010 surface.
        pure=enough & (water>=.999)
        land=enough & (water<.999)
        four=binary_dilation(land,structure=np.array([[0,1,0],[1,1,1],[0,1,0]],dtype=bool)) & pure
        eight=binary_dilation(land,structure=np.ones((3,3),dtype=bool)) & pure
        neighbours={
            GROUPS[0]:four,
            GROUPS[1]:eight & ~four,
            GROUPS[2]:pure & ~eight
        }
        stats={name:empty_stats() for name in BINS}
        neighbour_stats={name:empty_stats() for name in GROUPS}
        totals=defaultdict(int)
        selected_water_pixels=[]
        for y in range(0,b.height,256):
            for x in range(0,b.width,256):
                w=Window(x,y,min(256,b.width-x),min(256,b.height-y))
                inside=geometry_mask([mapping(polygon)],out_shape=(int(w.height),int(w.width)),
                    transform=rasterio.windows.transform(w,b.transform),invert=True,all_touched=False)
                if not inside.any():continue
                rows=slice(y,y+int(w.height))
                cols=slice(x,x+int(w.width))
                current_coverage=enough[rows,cols] & inside
                totals["municipal_cells_in_2010_raster_footprint"]+=int(inside.sum())
                totals["municipal_cells_with_sufficient_nmd2018_coverage"]+=int(current_coverage.sum())
                if not current_coverage.any():continue
                bm=b.read(1,window=w,masked=True)
                vm=v.read(1,window=w,masked=True)
                biomass=np.asarray(bm.data,dtype=np.float64)
                volume=np.asarray(vm.data,dtype=np.float64)
                valid_b=~np.ma.getmaskarray(bm) & np.isfinite(biomass) & (biomass>=0)
                valid_v=~np.ma.getmaskarray(vm) & np.isfinite(volume) & (volume>=0)
                water_window=water[rows,cols]
                # Export non-licensed 2010 source-grid pixel indices only; SMD
                # licensed polygons remain entirely in the local environment.
                mask=current_coverage & pure[rows,cols] & valid_b & valid_v
                for iy,ix in zip(*np.nonzero(mask)):
                    rr=y+int(iy); cc=x+int(ix)
                    neighbor=(1 if four[rr,cc] else 2 if eight[rr,cc] else 3)
                    selected_water_pixels.append([rr,cc,neighbor])
                for name,mask in zip(BINS,bin_masks(water_window)):
                    push_stats(stats[name],current_coverage&mask,biomass,volume,valid_b,valid_v)
                for name,mask in neighbours.items():
                    push_stats(neighbour_stats[name],
                      current_coverage&mask[rows,cols],biomass,volume,valid_b,valid_v)
        if sum(q["nmd_covered_cells"] for q in stats.values())!=totals["municipal_cells_with_sufficient_nmd2018_coverage"]:
            raise ValueError("Native water fraction classes do not partition eligible cells")
        if sum(q["nmd_covered_cells"] for q in neighbour_stats.values())!=stats["100 %"]["nmd_covered_cells"]:
            raise ValueError("Pure-water 4/8 neighbour classes do not partition native target cells")
        for q in list(stats.values())+list(neighbour_stats.values()):
            if q["both_2010_valid"]>min(q["biomass_valid"],q["volume_valid"]):
                raise ValueError("Overcounting joint source validity")
        if len(selected_water_pixels)!=stats["100 %"]["both_2010_valid"]:
            raise ValueError("Native pixel selection disagrees with grouped water statistics")
        results={"analysis":"NATIVE_2010_EPSG3021_MASK_VS_NMD2018_WATER_COVER",
          "created_utc":datetime.now(timezone.utc).isoformat(),
          "native_analysis_grid":"EPSG:3021","native_analysis_resolution_m":25,
          "nmd_source_crs":"EPSG:3006","nmd_native_resolution_m":10,
          "target_pixel_area_m2":625,
          "native_grid_transform":list(b.transform)[:6],
          "source_grid_water_valid_pixel_indices_row_col_neighbour":selected_water_pixels,
          "neighbour_code":{'1':'4 side neighbour contains nonwater','2':'diagonal-only nonwater','3':'no nonwater among 8'},
          "source_metadata":source_metadata,
          "study_population":dict(totals),
          "water_fraction_bands":{name:describe(q) for name,q in stats.items()},
          "pure_nmd2018_water_neighbours":{name:describe(q) for name,q in neighbour_stats.items()},
          "method":"Original 2010 biomass/volume pixels read directly without warp. Binary NMD2018 water and data coverage separately warped from original 10m EPSG:3006 to every native 25m EPSG:3021 pixel using average on complete output grids in 256px blocks. >=99.9% original NMD validity required; 100% NMD water means >=99.9% original NMD 10m water class.",
          "limitations":[
             "NMD2018 is NOT the 2010 shoreline or a 2010 forest mask.",
             "The 2010 rasters are source CRS clips; source NoData may include clipping decisions made prior to archiving.",
             "Rasterized water fraction is an NMD2018 category coverage estimate, not physical exact shoreline area.",
             "Four/eight-neighbour relationships are between source grid centres at EPSG:3021 25m and depend on map alignment.",
             "Native EPSG:3021 results cannot be numerically equated cell-for-cell to the older 25m EPSG:3006 comparison because the grids differ.",
             "Pixels with partial/no NMD2018 source coverage are omitted from water-fraction bin denominators.",
             "Original biomass/volume values are raw, with units/compartments not independently verified."
          ]}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
        print("Native source metadata",json.dumps(source_metadata,ensure_ascii=False),flush=True)
        print("Native pixel water fraction bands",json.dumps(results["water_fraction_bands"],ensure_ascii=False),flush=True)
        print("Pure-water 4/8-neighbour summary",json.dumps(results["pure_nmd2018_water_neighbours"],ensure_ascii=False),flush=True)
        print("Native mask population",json.dumps(results["study_population"],ensure_ascii=False),flush=True)
        # UTF-8 ASCII transport in GitHub Actions logs for private local SMD crosswalk.
        # Contains only 2010 raster grid row/col and NMD neighbour code (NO SMD).
        payload=json.dumps({"transform":results["native_grid_transform"],
                            "pixels":selected_water_pixels},separators=(",",":"))
        packed=base64.b64encode(zlib.compress(payload.encode("utf-8"),9)).decode("ascii")
        print("NATIVE_2010_WATER_PIXELS_ZLIB_BASE64="+packed,flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--biomass-2010",type=Path,required=True)
    p.add_argument("--volume-2010",type=Path,required=True)
    p.add_argument("--nmd",type=Path,required=True)
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--output",type=Path,default=Path("metadata/native_2010_water_fraction_mask.json"))
    main(p.parse_args())
