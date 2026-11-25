#!/usr/bin/env python3
"""Compare original NMD2018 base land-cover classes, biomass raster generations and 2010 volume.

All layers are warped to the SAME 25 m EPSG:3006 grid before analysis.
2010 biomass/2010 volume is strictly a raw-value diagnostic, not mass conversion.
"""
from __future__ import annotations
import argparse
import json
import math
from collections import defaultdict
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
from scipy.ndimage import distance_transform_edt, binary_dilation, label as connected_components
from rasterio.warp import reproject
from rasterio.windows import bounds as window_bounds
from fetch_and_compare_biomass_native import matches_expected_crs
from shapely.geometry import shape, mapping
from shapely.ops import transform as project_geom

YEARS=("2010","2015","2018")
def original_nmd_water_fraction(source, target_transform, target_width, target_height, tile=256):
    """Fraction of *original* 10m NMD classified as water per actual 25m pixel.

    Reprojects binary class and source-validity coverages independently with
    area average; it never interpolates categorical NMD code values.
    Does not claim to infer real shore geometry inside a 10m source cell.
    """
    water_fraction=np.zeros((target_height,target_width),dtype="float32")
    coverage_fraction=np.zeros_like(water_fraction)
    for rr in range(0,target_height,tile):
        for cc in range(0,target_width,tile):
            tw=Window(cc,rr,min(tile,target_width-cc),min(tile,target_height-rr))
            bound=window_bounds(tw,target_transform)
            # Source and analysis CRS both have previously been verified as EPSG:3006.
            swf=source.window(*bound)
            xoff=math.floor(swf.col_off)-2
            yoff=math.floor(swf.row_off)-2
            xmax=math.ceil(swf.col_off+swf.width)+2
            ymax=math.ceil(swf.row_off+swf.height)+2
            sw=Window(xoff,yoff,xmax-xoff,ymax-yoff)
            native=source.read(1,window=sw,boundless=True,fill_value=source.nodata)
            native_valid=(native!=source.nodata).astype("float32")
            native_water=np.isin(native,(61,62)).astype("float32")
            dw_transform=rasterio.windows.transform(tw,target_transform)
            sw_transform=rasterio.windows.transform(sw,source.transform)
            area_shape=(int(tw.height),int(tw.width))
            water_out=np.zeros(area_shape,dtype="float32")
            valid_out=np.zeros(area_shape,dtype="float32")
            for origin,target in ((native_water,water_out),(native_valid,valid_out)):
                reproject(source=origin,destination=target,src_transform=sw_transform,
                    src_crs=source.crs,dst_transform=dw_transform,dst_crs="EPSG:3006",
                    resampling=Resampling.average,init_dest_nodata=True)
            water_fraction[rr:rr+area_shape[0],cc:cc+area_shape[1]]=water_out
            coverage_fraction[rr:rr+area_shape[0],cc:cc+area_shape[1]]=valid_out
    return water_fraction,coverage_fraction

# Official NMD2018 v1.1 base code list: the complete fine forest codes,
# temporary nonforest, wetlands, cropland, open, developed and water.
LABELS={
 111:"Tallskog utanför våtmark",112:"Granskog utanför våtmark",
 113:"Barrblandskog utanför våtmark",114:"Lövblandad barrskog utanför våtmark",
 115:"Triviallövskog utanför våtmark",116:"Ädellövskog utanför våtmark",
 117:"Triviallövskog med ädellövinslag utanför våtmark",
 118:"Temporärt ej skog utanför våtmark",
 121:"Tallskog på våtmark",122:"Granskog på våtmark",
 123:"Barrblandskog på våtmark",124:"Lövblandad barrskog på våtmark",
 125:"Triviallövskog på våtmark",126:"Ädellövskog på våtmark",
 127:"Triviallövskog med ädellövinslag på våtmark",
 128:"Temporärt ej skog på våtmark",
 2:"Öppen våtmark",3:"Åkermark",41:"Öppen mark utan vegetation",
 42:"Öppen mark med vegetation",51:"Exploaterad mark, byggnad",
 52:"Exploaterad mark, annan",53:"Exploaterad mark, väg/järnväg",
 61:"Sjö/vattendrag",62:"Hav"
}
def group(code):
    if 111<=code<=117:return "Skog utanför våtmark"
    if 121<=code<=127:return "Skog på våtmark"
    if code in (118,128):return "Temporärt ej skog"
    if code==2:return "Öppen våtmark"
    if code==3:return "Åkermark"
    if code in (41,42):return "Övrig öppen mark"
    if code in (51,52,53):return "Exploaterad mark"
    if code in (61,62):return "Vatten"
    return "Okänd"
def run(args):
    obj=json.loads(args.boundary.read_text(encoding="utf-8"))
    if obj.get("type")!="FeatureCollection" or len(obj.get("features",[]))!=1:
        raise ValueError("Expected one GeoJSON EPSG:4326 boundary")
    g=shape(obj["features"][0]["geometry"])
    if g.is_empty or not g.is_valid:raise ValueError("Invalid boundary")
    geom=project_geom(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,g)
    step=25.0
    x0,y0,x1,y1=geom.bounds
    x0=math.floor(x0/step)*step;y0=math.floor(y0/step)*step
    x1=math.ceil(x1/step)*step;y1=math.ceil(y1/step)*step
    width=round((x1-x0)/step);height=round((y1-y0)/step)
    if width*height>40000000:raise ValueError("Unreasonable grid")
    trans=Affine(step,0,x0,0,-step,y1)
    from contextlib import ExitStack
    data=defaultdict(lambda:{"cells":0,"biomass_sum":{y:0.0 for y in YEARS},
                             "volume_sum":0.0,"ratio_sum":0.0,"ratio_cells":0,
                             "highvol_cells":0,"highvol_biomass_sum":{y:0.0 for y in YEARS}})
    rejected=defaultdict(int)
    neighbour_stats={name:{"cells":0,"sum":{y:0.0 for y in YEARS},"volume_ge100_cells":0}
       for name in ("pure_water_four_land_neighbour","pure_water_diagonal_only_land_neighbour",
          "pure_water_no_eight_land_neighbour","mixed_land_water",
          "nearest_water_with_pure_water","nearest_water_with_mixed_water")}
    no_land_eight_selected=np.zeros((height,width),dtype=bool)
    no_land_eight_b2010=np.full((height,width),np.nan,dtype='float32')
    no_land_eight_b2018=np.full((height,width),np.nan,dtype='float32')
    no_land_eight_v2010=np.full((height,width),np.nan,dtype='float32')
    resample_compare={k:{"cells":0,"biomass_sum_2010":0.0,"biomass_sum_2018":0.0} for k in ("water_both","water_nearest_only","water_mode_only","nonwater_both")}
    # Exactly NMD2018 codes 118/128, not NMD productivity class 0.
    # Volume is 2010 source-estimated m3/ha and is a stratifier, NOT a
    # historical measured harvest footprint or a biomass conversion.
    temp_volume_bins=[("2010_volume_0",0,0),("2010_volume_gt0_lt50",0,50),
       ("2010_volume_50_100",50,100),("2010_volume_100_200",100,200),
       ("2010_volume_200_plus",200,None),("2010_volume_missing",None,None)]
    temp_volume_stats={k:{"cells":0,"sums_raw":{y:0. for y in YEARS},
       "zero_2015_cells":0,"zero_2018_cells":0,"zero_both_2015_2018_cells":0,
       "b2010_positive_and_b2018_zero":0,"sum_raw_delta_where_b2018_zero":0.}
       for k,_,_ in temp_volume_bins}
    temp_nmd_code_stats={str(k):{"cells":0,"sums_raw":{y:0. for y in YEARS}}
       for k in (118,128)}
    mode_water_all=0
    shore_bins={side:{band:{'cells':0,'sums':{y:0.0 for y in YEARS},'high_volume_cells':0} for band in ('0-25 m','>25-50 m','>50-75 m','>75-100 m','>100 m')} for side in ('water','forest')}
    water_near_forest={'within_50m':{'cells':0,'sums':{y:0.0 for y in YEARS}},'farther_than_50m':{'cells':0,'sums':{y:0.0 for y in YEARS}}}
    nearest_water_all=0
    water_bins={name:{'cells':0,'sum':{y:0.0 for y in YEARS},'volume_high_cells':0} for name in ('0-50 m','50-100 m','100-250 m','250+ m')}
    with ExitStack() as stack:
        srcs={}
        for y in YEARS:
            src=stack.enter_context(rasterio.open(getattr(args,"biomass_"+y)))
            expected=3021 if y=="2010" else 3006
            if src.crs is None or not matches_expected_crs(src.crs,expected) or src.count!=1 or src.nodata is None:
                raise ValueError(y+" biomass original CRS/band/NoData invalid")
            if abs(src.res[0]-(25 if y=="2010" else 12.5 if y=="2015" else 10))>.1:
                raise ValueError("Biomass pixel size mismatched "+y)
            srcs[y]=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=trans,
                width=width,height=height,resampling=Resampling.average,
                src_nodata=src.nodata,nodata=-9999,dtype="float32"))
        src=stack.enter_context(rasterio.open(args.volume_2010))
        if src.crs is None or not matches_expected_crs(src.crs,3021) or src.count!=1 or src.nodata is None:
            raise ValueError("2010 wood volume source metadata invalid")
        vol=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=trans,
            width=width,height=height,resampling=Resampling.average,
            src_nodata=src.nodata,nodata=-9999,dtype="float32"))
        src=stack.enter_context(rasterio.open(args.nmd))
        if src.crs is None or not matches_expected_crs(src.crs,3006) or src.count!=1 or any(abs(abs(r)-10)>.01 for r in src.res):
            raise ValueError("NMD2018 county raster wrong CRS/band/resolution")
        if src.nodata in LABELS:raise ValueError("NMD NoData clashes with known class codes")
        nmd=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=trans,
            width=width,height=height,resampling=Resampling.nearest,
            src_nodata=src.nodata,nodata=255,dtype="uint8"))
        # Mode gives the dominant source class in each target pixel, while nearest
        # picks one source sample. Both are categorical warps of original 10m NMD.
        nmd_mode=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=trans,
            width=width,height=height,resampling=Resampling.mode,
            src_nodata=src.nodata,nodata=255,dtype="uint8"))
        # Native NMD 10m source -> full 25m water-area fraction; this is an
        # independent native-resolution mask check (not nearest/mode reclassification).
        nmd_fraction,nmd_source_coverage=original_nmd_water_fraction(src,trans,width,height)
        pure=(nmd_fraction>=0.999) & (nmd_source_coverage>=0.999)
        land_present=(nmd_fraction<0.999) & (nmd_source_coverage>=0.999)
        direct=binary_dilation(land_present,structure=np.array([[0,1,0],[1,1,1],[0,1,0]],dtype=bool)) & pure
        eight=binary_dilation(land_present,structure=np.ones((3,3),dtype=bool)) & pure
        pure_groups={
          "pure_water_four_land_neighbour":direct,
          "pure_water_diagonal_only_land_neighbour":eight & ~direct,
          "pure_water_no_eight_land_neighbour":pure & ~eight
        }
        # All groups operate on common valid biomass cells; outside this
        # population they must not be interpreted as a full water inventory.
        # Distance from a water-class centre to the nearest non-water NMD2018 cell,
        # not distance to an independently verified shoreline. Full-grid resampling
        # precedes this raster analysis in EPSG:3006.
        full_nmd=np.ma.asarray(nmd.read(1,masked=True))
        full_water=np.isin(full_nmd.data,(61,62)) & ~np.ma.getmaskarray(full_nmd)
        water_distance=distance_transform_edt(full_water)*step
        forest_codes=list(range(111,118))+list(range(121,128))
        full_forest=np.isin(full_nmd.data,forest_codes) & ~np.ma.getmaskarray(full_nmd)
        # Distances are between centres of the resampled NMD grid cells in EPSG:3006.
        # Distance to forest for water cells, and to water for forest cells.
        dist_to_forest=distance_transform_edt(~full_forest)*step
        dist_to_water=distance_transform_edt(~full_water)*step
        del full_nmd,full_water,full_forest
        for row in range(0,height,256):
            for col in range(0,width,256):
                w=Window(col,row,min(256,width-col),min(256,height-row))
                inside=geometry_mask([mapping(geom)],out_shape=(int(w.height),int(w.width)),
                  transform=rasterio.windows.transform(w,trans),invert=True,all_touched=False)
                if not inside.any():continue
                bs={y:np.ma.asarray(srcs[y].read(1,window=w,masked=True),dtype="float64").filled(np.nan) for y in YEARS}
                v=np.ma.asarray(vol.read(1,window=w,masked=True),dtype="float64").filled(np.nan)
                m=nmd.read(1,window=w,masked=True)
                mm=nmd_mode.read(1,window=w,masked=True)
                good=inside.copy()
                for arr in bs.values():good &= np.isfinite(arr)&(arr>=0)
                rejected["joint_biomass_cells"]+=int(good.sum())
                valid=good & (~np.ma.getmaskarray(m)) & (m.data!=255)
                rejected["missing_NMD"]+=int((good&~valid).sum())
                mode_valid=good & ~np.ma.getmaskarray(mm) & (mm.data!=255)
                overlap=valid & mode_valid
                nw=np.isin(m.data,(61,62))
                mw=np.isin(mm.data,(61,62))
                nearest_water_all+=int((valid & nw).sum())
                mode_water_all+=int((mode_valid & mw).sum())
                for name,sel in (("water_both",overlap & nw & mw),
                  ("water_nearest_only",overlap & nw & ~mw),
                  ("water_mode_only",overlap & ~nw & mw),
                  ("nonwater_both",overlap & ~nw & ~mw)):
                    d=resample_compare[name];n=int(sel.sum());d["cells"]+=n
                    if n:
                        d["biomass_sum_2010"]+=float(bs["2010"][sel].sum(dtype="float64"))
                        d["biomass_sum_2018"]+=float(bs["2018"][sel].sum(dtype="float64"))
                fraction=nmd_fraction[int(row):int(row+w.height),int(col):int(col+w.width)]
                cover=nmd_source_coverage[int(row):int(row+w.height),int(col):int(col+w.width)]
                # Pure water cells are selected from native 10m classes, not
                # by a single resampled NMD cell-centre value.
                for name,pure_group in pure_groups.items():
                    sel=good & pure_group[int(row):int(row+w.height),int(col):int(col+w.width)]
                    n=int(sel.sum())
                    if n:
                        d=neighbour_stats[name];d["cells"]+=n
                        for y in YEARS:d["sum"][y]+=float(bs[y][sel].sum(dtype="float64"))
                        d["volume_ge100_cells"]+=int((np.isfinite(v[sel]) & (v[sel]>=100)).sum())
                mixed=good & (cover>=0.999) & (fraction>0.001) & (fraction<0.999)
                nearwater=valid & nw
                # Store both diagnostic populations explicitly rather than
                # silently equating 10m area cover with 25m nearest class.
                special={
                  "mixed_land_water":mixed,
                  "nearest_water_with_pure_water":nearwater & (fraction>=0.999)&(cover>=0.999),
                  "nearest_water_with_mixed_water":nearwater & mixed
                }
                for name,sel in special.items():
                    n=int(sel.sum())
                    if n:
                        d=neighbour_stats[name];d["cells"]+=n
                        for y in YEARS:d["sum"][y]+=float(bs[y][sel].sum(dtype="float64"))
                        d["volume_ge100_cells"]+=int((np.isfinite(v[sel]) & (v[sel]>=100)).sum())
                # Preserve only the exact high-interest, jointly valid cells
                # for cluster/footprint analysis after the raster window loop.
                far=good & pure_groups['pure_water_no_eight_land_neighbour'][int(row):int(row+w.height),int(col):int(col+w.width)]
                if far.any():
                    sl=(slice(int(row),int(row+w.height)),slice(int(col),int(col+w.width)))
                    no_land_eight_selected[sl]=far
                    for grid,srcdata in ((no_land_eight_b2010,bs['2010']),
                                         (no_land_eight_b2018,bs['2018']),
                                         (no_land_eight_v2010,v)):
                        view=grid[sl];view[far]=srcdata[far]
                known=np.zeros_like(good)
                for code in LABELS:
                    sel=valid & (m.data==code)
                    known |= sel
                    n=int(sel.sum())
                    if not n:continue
                    d=data[code];d["cells"]+=n
                    for y in YEARS:d["biomass_sum"][y]+=float(bs[y][sel].sum(dtype="float64"))
                    vgood=sel & np.isfinite(v)&(v>=0)
                    d["volume_sum"]+=float(v[vgood].sum(dtype="float64"))
                    # A meaningful 2010 ratio can only be computed for positive volume.
                    ratio=vgood & (v>=10)
                    d["ratio_cells"]+=int(ratio.sum())
                    d["ratio_sum"]+=float((bs["2010"][ratio]/v[ratio]).sum(dtype="float64"))
                    hv=vgood & (v>=100)
                    d["highvol_cells"]+=int(hv.sum())
                    for y in YEARS:d["highvol_biomass_sum"][y]+=float(bs[y][hv].sum(dtype="float64"))
                # Targeted NMD2018 temporary-not-forest assessment.
                # Only same jointly valid biomass (2010/15/18), NMD2018
                # group and 2010 volume used for stratification.
                for nmd_code in (118,128):
                    temp=valid & (m.data==nmd_code)
                    if not temp.any():continue
                    by_code=temp_nmd_code_stats[str(nmd_code)]
                    by_code["cells"]+=int(temp.sum())
                    for y in YEARS:
                        by_code["sums_raw"][y]+=float(bs[y][temp].sum(dtype="float64"))
                    for bin_label,low,high in temp_volume_bins:
                        if bin_label=="2010_volume_missing":
                            selected=temp & ~(np.isfinite(v)&(v>=0))
                        elif bin_label=="2010_volume_0":
                            selected=temp & (v==0)
                        else:
                            selected=temp & np.isfinite(v) & (v>low) & (
                                (v<high) if bin_label=="2010_volume_gt0_lt50"
                                else ((v>=low)&(v<high)) if high is not None else (v>=low))
                        if not selected.any():continue
                        t=temp_volume_stats[bin_label]
                        count=int(selected.sum())
                        t["cells"]+=count
                        for y in YEARS:
                            t["sums_raw"][y]+=float(bs[y][selected].sum(dtype="float64"))
                        z15=selected&(bs["2015"]==0)
                        z18=selected&(bs["2018"]==0)
                        t["zero_2015_cells"]+=int(z15.sum())
                        t["zero_2018_cells"]+=int(z18.sum())
                        t["zero_both_2015_2018_cells"]+=int((z15&z18).sum())
                        t["b2010_positive_and_b2018_zero"]+=int((z18&(bs["2010"]>0)).sum())
                        t["sum_raw_delta_where_b2018_zero"]+=float(bs["2010"][z18].sum(dtype="float64"))
                # Diagnose how much apparent 2010 wood biomass sits within water
                # cells at increasing distances from a non-water NMD cell.
                water=valid & np.isin(m.data,(61,62))
                dwindow=water_distance[int(row):int(row+w.height),int(col):int(col+w.width)]
                for name,lo,hi in (('0-50 m',0,50),('50-100 m',50,100),
                                   ('100-250 m',100,250),('250+ m',250,float('inf'))):
                    selected=water & (dwindow>=lo)&(dwindow<hi)
                    count=int(selected.sum())
                    if count:
                        d=water_bins[name]
                        d['cells']+=count
                        for y in YEARS:d['sum'][y]+=float(bs[y][selected].sum(dtype='float64'))
                        d['volume_high_cells']+=int(np.count_nonzero(np.isfinite(v[selected]) & (v[selected]>=100)))
                forest=valid & np.isin(m.data,forest_codes)
                fd=dist_to_water[int(row):int(row+w.height),int(col):int(col+w.width)]
                for side,sel,dist in (('water',water,water_distance[int(row):int(row+w.height),int(col):int(col+w.width)]),('forest',forest,fd)):
                    for band,low,high in (('0-25 m',0,25),('>25-50 m',25,50),('>50-75 m',50,75),('>75-100 m',75,100),('>100 m',100,float('inf'))):
                        # Distances are Euclidean between 25m cell centres; endpoints
                        # belong to the lower band: 25, 50, 75, 100 m respectively.
                        mask=sel & (dist>low if low else dist>=0) & (dist<=high)
                        count=int(mask.sum())
                        if count:
                            bucket=shore_bins[side][band]
                            bucket['cells']+=count
                            for y in YEARS:bucket['sums'][y]+=float(bs[y][mask].sum(dtype='float64'))
                            bucket['high_volume_cells']+=int(np.count_nonzero(np.isfinite(v[mask]) & (v[mask]>=100)))
                # Hypothesis: does the water anomaly preferentially occur next to
                # forest classes rather than any shoreline land class?
                forest_distance=dist_to_forest[int(row):int(row+w.height),int(col):int(col+w.width)]
                for label,mask in (('within_50m', water & (forest_distance<=50)),
                                   ('farther_than_50m', water & (forest_distance>50))):
                    count=int(mask.sum())
                    if count:
                        bucket=water_near_forest[label]
                        bucket['cells']+=count
                        for y in YEARS:bucket['sums'][y]+=float(bs[y][mask].sum(dtype='float64'))
                unknown=valid & ~known
                if unknown.any():
                    for code,n in zip(*np.unique(m.data[unknown],return_counts=True)):
                        rejected["unknown_code_"+str(int(code))]+=int(n)
    if any(k.startswith("unknown_code") for k in rejected):raise ValueError("Unexpected NMD codes "+str(rejected))
    rows=[]
    for code,label in LABELS.items():
        d=data[code];n=d["cells"]
        if not n:continue
        rows.append({"class_code":code,"class_name":label,"group":group(code),
          "cells":n,"area_ha":n*.0625,
          "biomass_means_raw":{y:d["biomass_sum"][y]/n for y in YEARS},
          "difference_2010_minus_2018_raw":(d["biomass_sum"]["2010"]-d["biomass_sum"]["2018"])/n,
          "volume_2010_mean_raw_on_volume_valid_cells":None,
          "ratio_2010_biomass_to_2010_volume_mean_on_volume_ge10":d["ratio_sum"]/d["ratio_cells"] if d["ratio_cells"] else None,
          "volume_2010_ratio_cells":d["ratio_cells"],
          "volume_2010_ge100_cells":d["highvol_cells"],
          "volume_2010_ge100_area_ha":d["highvol_cells"]*.0625,
          "biomass_means_raw_volume_ge100":{y:d["highvol_biomass_sum"][y]/d["highvol_cells"] if d["highvol_cells"] else None for y in YEARS},
          "sum_diff_2010_minus_2018":d["biomass_sum"]["2010"]-d["biomass_sum"]["2018"]})
    total=sum(x["cells"] for x in rows)
    if total<2000000:raise ValueError("Too few matched classified pixels "+str(total))
    groups=[]
    for groupname in dict.fromkeys(r["group"] for r in rows):
        subset=[r for r in rows if r["group"]==groupname]
        n=sum(r["cells"] for r in subset)
        groups.append({"group":groupname,"cells":n,"area_ha":n*.0625,
          "means_raw":{y:sum(r["biomass_means_raw"][y]*r["cells"] for r in subset)/n for y in YEARS},
          "raw_sum_diff_2010_minus_2018":sum(r["sum_diff_2010_minus_2018"] for r in subset)})
    totaldiff=sum(r["sum_diff_2010_minus_2018"] for r in rows)
    for r in rows:r["share_of_total_2010_minus_2018_raw_difference"]=r["sum_diff_2010_minus_2018"]/totaldiff if totaldiff else None
    for d in groups:d["share_of_total_2010_minus_2018_raw_difference"]=d["raw_sum_diff_2010_minus_2018"]/totaldiff if totaldiff else None
    forests=[r for r in rows if r["class_code"] in set(range(111,118))|set(range(121,128))]
    fn=sum(r["cells"] for r in forests)
    fmeans={y:sum(r["biomass_means_raw"][y]*r["cells"] for r in forests)/fn for y in YEARS}
    water_rows=[]
    for label,d in water_bins.items():
        n=d["cells"]
        water_rows.append({"distance_to_nmd_nonwater":label,"cells":n,"area_ha":n*.0625,
          "means_raw":{y:d["sum"][y]/n if n else None for y in YEARS},
          "volume_2010_ge100_cells":d["volume_high_cells"],
          "raw_sum_diff_2010_minus_2018":d["sum"]["2010"]-d["sum"]["2018"]})
    waterclass_count=sum(r["cells"] for r in rows if r["class_code"] in (61,62))
    if sum(d["cells"] for d in water_rows)!=waterclass_count:
        raise ValueError("Water distance classes do not reconcile with NMD61+NMD62")
    forest_result={"definition":"Only NMD2018 classes 111-117 and 121-127, excluding 118,128",
        "area_ha":fn*.0625,"cells":fn,"means_raw":fmeans,
        "raw_mean_difference_2010_minus_2018":fmeans["2010"]-fmeans["2018"],
        "relative_difference_of_raw_mean_percent":100*(fmeans["2010"]/fmeans["2018"]-1) if fmeans["2018"] else None}
    def describe_bins(data):
        return {name:{'cells':d['cells'],'area_ha':d['cells']*.0625,
           'biomass_means_raw':{y:d['sums'][y]/d['cells'] if d['cells'] else None for y in YEARS},
           **({'volume_2010_ge100_cells':d['high_volume_cells']} if 'high_volume_cells' in d else {})}
           for name,d in data.items()}
    riparian={'water_side_distance_to_nonwater':describe_bins(shore_bins['water']),
      'forest_side_distance_to_water':describe_bins(shore_bins['forest']),
      'water_distance_to_NMD2018_forest':describe_bins(water_near_forest),
      'method':'Five disjoint Euclidean centre-to-centre distance bands <=25, >25-50, >50-75, >75-100, >100 metres on 25m EPSG:3006 grid; 25m cell offsets include diagonal distances; NOT literal raster-ring steps, historical shoreline or forestry leave-strip map'}
    if sum(x['cells'] for x in shore_bins['water'].values())!=waterclass_count:
        raise ValueError('Shoreline water bands do not match waterclass count')
    # Eight-neighbour connected components of exact jointly-valid water cells,
    # no coordinate location inferred from NMD alone or from a raster bbox.
    component_labels,component_count=connected_components(no_land_eight_selected,
      structure=np.ones((3,3),dtype=np.uint8))
    component_rows=[]
    for cid in range(1,component_count+1):
        yy,xx=np.where(component_labels==cid)
        count=int(len(xx))
        if not count:continue
        east=x0+(xx.astype('float64')+.5)*step
        north=y1-(yy.astype('float64')+.5)*step
        vals2010=no_land_eight_b2010[yy,xx]
        vals2018=no_land_eight_b2018[yy,xx]
        volvals=no_land_eight_v2010[yy,xx]
        component_rows.append({'component_id':cid,'cells':count,'area_ha':count*.0625,
          'centroid_easting_epsg3006':float(east.mean()),
          'centroid_northing_epsg3006':float(north.mean()),
          'bounds_epsg3006':[float(east.min()-step/2),float(north.min()-step/2),
                            float(east.max()+step/2),float(north.max()+step/2)],
          'mean_biomass_raw_2010':float(np.nanmean(vals2010)),
          'mean_biomass_raw_2018':float(np.nanmean(vals2018)),
          'mean_volume_raw_2010':float(np.nanmean(volvals))})
    component_rows.sort(key=lambda x:(-x['cells'],-x['mean_biomass_raw_2010']))
    if int(no_land_eight_selected.sum())!=neighbour_stats['pure_water_no_eight_land_neighbour']['cells']:
        raise ValueError('Cluster source population differs from 8-neighbour diagnostic')
    if sum(x['cells'] for x in component_rows)!=int(no_land_eight_selected.sum()):
        raise ValueError('8-connected clusters do not reconcile with selected cells')
    clustering={'method':'8-connected groups of strictly pure-water cells without adjacent land, selected on jointly valid biomass; coordinates and bounds in EPSG:3006',
      'components':len(component_rows),
      'largest_component_cells':component_rows[0]['cells'] if component_rows else 0,
      'total_cells':int(no_land_eight_selected.sum()),
      'top_components':component_rows[:30],
      'all_components_are_reported':len(component_rows)<=30}
    pure_total=sum(neighbour_stats[k]["cells"] for k in pure_groups)
    water_neighbours={
      "definition":"Native NMD2018 10m source: 25m cells with >=99.9 percent water-class coverage and >=99.9 percent valid source coverage; adjacency to any cell with verified non-water fraction >=0.1 percent",
      "pure_water_25m_cells_common_biomass":pure_total,
      "groups":{name:{"cells":d["cells"],"area_ha":d["cells"]*.0625,
         "means_raw":{y:d["sum"][y]/d["cells"] if d["cells"] else None for y in YEARS},
         "volume_2010_ge100_cells":d["volume_ge100_cells"]} for name,d in neighbour_stats.items()},
      "geometry_caveat":"Native 10m categorical water fraction approximates polygon cover, 25m adjacency four sides vs diagonal only on EPSG:3006 grid. It does not demonstrate actual water in 2010, original 2010 biomass mask or original shoreline geometry"
    }
    assert pure_total>=0
    sensitivity={"classification_methods":["nearest","mode"],
      "water_nearest_cells":nearest_water_all,"water_mode_cells":mode_water_all,
      "water_nearest_area_ha":nearest_water_all*.0625,
      "water_mode_area_ha":mode_water_all*.0625,
      "overlap_cells_by_water_agreement":{
        key:{"cells":d["cells"],"area_ha":d["cells"]*.0625,
          "biomass_means_raw":{"2010":d["biomass_sum_2010"]/d["cells"] if d["cells"] else None,
             "2018":d["biomass_sum_2018"]/d["cells"] if d["cells"] else None}}
        for key,d in resample_compare.items()},
      "interpretation":"Sensitivity of class assignment, not a correction of native 2010 forest biomass or coastline"}
    if sum(d["cells"] for d in resample_compare.values())>total:raise ValueError("Invalid nearest/mode overlap counts")
    temp_population=sum(z["cells"] for z in temp_nmd_code_stats.values())
    temp_categorized=sum(z["cells"] for z in temp_volume_stats.values())
    if temp_population!=temp_categorized:
        raise ValueError("NMD2018 temporary-not-forest volumes do not partition 118+128")
    temp_from_classes=sum(data[k]["cells"] for k in (118,128))
    if temp_population!=temp_from_classes:
        raise ValueError("Temporary-not-forest cell count differs from class rows")
    for year in YEARS:
        by_bin=sum(z["sums_raw"][year] for z in temp_volume_stats.values())
        by_code=sum(z["sums_raw"][year] for z in temp_nmd_code_stats.values())
        ref_sum=sum(data[k]["biomass_sum"][year] for k in (118,128))
        if abs(by_bin-ref_sum)>max(1,abs(ref_sum))*1e-7 or abs(by_code-ref_sum)>max(1,abs(ref_sum))*1e-7:
            raise ValueError("Temporary-not-forest biomass sums do not reconcile")
    temp_diagnostics={
      "definition":"NMD2018 base codes 118 and 128 = temporarily not forest (not productivity code 0)",
      "cells":temp_population,"area_ha":temp_population*.0625,
      "volume_groups":temp_volume_stats,"nmd_code_groups":temp_nmd_code_stats,
      "volume_reference_year":2010,
      "harvest_confirmation":"NOT TESTED - modeled 2010 volume does not independently prove logging",
      "zero_rules":"An observed raster zero is distinguished from masked NoData; zero is not automatically attributed to the 3m height rule."
    }
    out={"status":"DESCRIPTIVE_NMD2018_FIXED_LANDCOVER_NOT_HISTORICAL","generated_utc":datetime.now(timezone.utc).isoformat(),
      "source_NMD2018":"BD_lan_nmd2018bas_ogeneraliserad_v1_1.zip","source_CRS_NMD":str(src.crs),
      "source_CRS_biomass":{"2010":"EPSG:3021","2015":"EPSG:3006","2018":"EPSG:3006"},
      "source_CRS_volume_2010":"EPSG:3021","analysis_CRS":"EPSG:3006","resolution_m":25,
      "forest_only_NMD2018_reference":forest_result,
      "temporary_not_forest_2018_volume_and_zero_diagnostics":temp_diagnostics,
      "water_distance_NMD2018":water_rows,
      "nmd_nearest_vs_mode_sensitivity":sensitivity,
      "nmd2018_riparian_forest_gradient":riparian,
      "original_10m_water_fraction_and_4_8_neighbours":water_neighbours,
      "pure_water_no_eight_land_neighbour_clusters":clustering,
      "matched_area_ha":total*.0625,"matched_cells":total,"diagnostic_counts":dict(rejected),
      "class_rows":rows,"group_rows":groups,
      "limitations":["NMD2018 classes are fixed and DO NOT establish land cover in 2010 or 2015",
        "2010 volume is NOT contemporaneous with biomass 2015 or 2018; no 2015/2018 biomass-volume ratios are calculated",
        "Biomass products are not harmonized in units or components; only raw values",
        "Categorical 10m NMD is sampled nearest to 25m; edge and small-class sensitivity remains",
        "2010 volume ratio reflects only modeled biomass and volume, not an independent measured conversion",
        "Only shared valid biomass cells and project working boundary counted",
        "Distance is from water NMD2018 cell centre to a non-water NMD2018 cell centre at 25m grid; not independently verified shoreline; nearest resampling and outside-source edges bias distance"]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Matched:",total,"cells",total*.0625,"ha; expected approx 153525.625 ha")
    print("NMD groups:",json.dumps(groups,ensure_ascii=False))
    print("Forest-only reference:",json.dumps(forest_result,ensure_ascii=False))
    print("Temporary-not-forest source-volume and zero diagnostics:",json.dumps(temp_diagnostics,ensure_ascii=False))
    print("Water distance:",json.dumps(water_rows,ensure_ascii=False))
    print("Nearest vs mode:",json.dumps(sensitivity,ensure_ascii=False))
    print("Riparian forest gradient:",json.dumps(riparian,ensure_ascii=False))
    print("Native 10m pure-water and 4/8 neighbours:",json.dumps(water_neighbours,ensure_ascii=False))
    print("Pure-water isolated clusters:",json.dumps(clustering,ensure_ascii=False))
    print("NMD classes:",json.dumps(rows,ensure_ascii=False))
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for y in YEARS:p.add_argument("--biomass-"+y,type=Path,required=True)
    p.add_argument("--volume-2010",type=Path,required=True)
    p.add_argument("--nmd",type=Path,required=True)
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--output",type=Path,default=Path("metadata/nmd2018_landcover_biomass_volume.json"))
    run(p.parse_args())
