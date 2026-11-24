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
from scipy.ndimage import distance_transform_edt
from fetch_and_compare_biomass_native import matches_expected_crs
from shapely.geometry import shape, mapping
from shapely.ops import transform as project_geom

YEARS=("2010","2015","2018")
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
        # Distance from a water-class centre to the nearest non-water NMD2018 cell,
        # not distance to an independently verified shoreline. Full-grid resampling
        # precedes this raster analysis in EPSG:3006.
        full_nmd=np.ma.asarray(nmd.read(1,masked=True))
        full_water=np.isin(full_nmd.data,(61,62)) & ~np.ma.getmaskarray(full_nmd)
        water_distance=distance_transform_edt(full_water)*step
        del full_nmd,full_water
        for row in range(0,height,256):
            for col in range(0,width,256):
                w=Window(col,row,min(256,width-col),min(256,height-row))
                inside=geometry_mask([mapping(geom)],out_shape=(int(w.height),int(w.width)),
                  transform=rasterio.windows.transform(w,trans),invert=True,all_touched=False)
                if not inside.any():continue
                bs={y:np.ma.asarray(srcs[y].read(1,window=w,masked=True),dtype="float64").filled(np.nan) for y in YEARS}
                v=np.ma.asarray(vol.read(1,window=w,masked=True),dtype="float64").filled(np.nan)
                m=nmd.read(1,window=w,masked=True)
                good=inside.copy()
                for arr in bs.values():good &= np.isfinite(arr)&(arr>=0)
                rejected["joint_biomass_cells"]+=int(good.sum())
                valid=good & (~np.ma.getmaskarray(m)) & (m.data!=255)
                rejected["missing_NMD"]+=int((good&~valid).sum())
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
    out={"status":"DESCRIPTIVE_NMD2018_FIXED_LANDCOVER_NOT_HISTORICAL","generated_utc":datetime.now(timezone.utc).isoformat(),
      "source_NMD2018":"BD_lan_nmd2018bas_ogeneraliserad_v1_1.zip","source_CRS_NMD":str(src.crs),
      "source_CRS_biomass":{"2010":"EPSG:3021","2015":"EPSG:3006","2018":"EPSG:3006"},
      "source_CRS_volume_2010":"EPSG:3021","analysis_CRS":"EPSG:3006","resolution_m":25,
      "forest_only_NMD2018_reference":forest_result,
      "water_distance_NMD2018":water_rows,
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
    print("Water distance:",json.dumps(water_rows,ensure_ascii=False))
    print("NMD classes:",json.dumps(rows,ensure_ascii=False))
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for y in YEARS:p.add_argument("--biomass-"+y,type=Path,required=True)
    p.add_argument("--volume-2010",type=Path,required=True)
    p.add_argument("--nmd",type=Path,required=True)
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--output",type=Path,default=Path("metadata/nmd2018_landcover_biomass_volume.json"))
    run(p.parse_args())
