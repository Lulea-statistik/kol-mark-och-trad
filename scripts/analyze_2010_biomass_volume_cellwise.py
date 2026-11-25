#!/usr/bin/env python3
"""Cellwise relation of SLU 2010 biomass and volume raw values.

Uses fully reprojected 25m EPSG:3006 raster grids, and the *same* common
2010/2015/2018 valid biomass population as the NMD2018 comparison. Outputs
statistical diagnostics, never biomass conversions or data corrections.
"""
from __future__ import annotations

import argparse
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
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from shapely.geometry import mapping, shape
from shapely.ops import transform as project_geom
from fetch_and_compare_biomass_native import matches_expected_crs

YEARS=("2010","2015","2018")
FOREST_CODES=set(range(111,118)) | set(range(121,128))
WATER_CODES={61,62}
MAX_RESIDUAL_SAMPLE=0 # Statistical moments are exact over all eligible pixels.

class Bivariate:
    """Streaming population moments with stable centered batches."""
    __slots__=("n","sum_x","sum_y","sum_xx","sum_yy","sum_xy","sum_ratio","ratio_n","ratio_sq","n_vol_ge100")
    def __init__(self):
        self.n=0
        self.sum_x=self.sum_y=self.sum_xx=self.sum_yy=self.sum_xy=0.
        self.sum_ratio=self.ratio_sq=0.
        self.ratio_n=self.n_vol_ge100=0
    def add(self,x,y):
        if not len(x):return
        x=np.asarray(x,dtype=np.float64)
        y=np.asarray(y,dtype=np.float64)
        self.n+=len(x)
        self.sum_x+=float(x.sum())
        self.sum_y+=float(y.sum())
        self.sum_xx+=float(np.dot(x,x))
        self.sum_yy+=float(np.dot(y,y))
        self.sum_xy+=float(np.dot(x,y))
        valid=x>=10
        if np.any(valid):
            ratios=y[valid]/x[valid]
            self.ratio_n+=len(ratios)
            self.sum_ratio+=float(ratios.sum())
            self.ratio_sq+=float(np.dot(ratios,ratios))
        self.n_vol_ge100+=int(np.count_nonzero(x>=100))
    def result(self):
        n=self.n
        if not n:return {"cells":0}
        vx=max(0.,self.sum_xx-self.sum_x*self.sum_x/n)
        vy=max(0.,self.sum_yy-self.sum_y*self.sum_y/n)
        cov=self.sum_xy-self.sum_x*self.sum_y/n
        pearson=cov/math.sqrt(vx*vy) if vx>1e-10 and vy>1e-10 else None
        slope=cov/vx if vx>1e-10 else None
        intercept=(self.sum_y/n-slope*self.sum_x/n) if slope is not None else None
        r2=pearson*pearson if pearson is not None else None
        rmse=math.sqrt(max(0.,(vy-cov*cov/vx)/n)) if vx>1e-10 else None
        mean_ratio=self.sum_ratio/self.ratio_n if self.ratio_n else None
        ratio_sd=math.sqrt(max(0.,self.ratio_sq/self.ratio_n-mean_ratio**2)) if self.ratio_n else None
        return {"cells":n,"area_ha":n*.0625,
            "mean_volume_2010_raw":self.sum_x/n,
            "mean_biomass_2010_raw":self.sum_y/n,
            "pearson_r":pearson,"ols_slope_raw":slope,
            "ols_intercept_raw":intercept,
            "ols_r_squared":r2,"ols_residual_rmse_raw":rmse,
            "ratio_biomass_to_volume_mean_for_volume_ge10":mean_ratio,
            "ratio_sd_for_volume_ge10":ratio_sd,
            "ratio_cell_count_volume_ge10":self.ratio_n,
            "volume_ge100_cells":self.n_vol_ge100}

def landgroup(c):
    if c in WATER_CODES:return "Vatten NMD2018"
    if c in FOREST_CODES:return "Skog NMD2018"
    return "Ovrig mark NMD2018"

def run(args):
    obj=json.loads(args.boundary.read_text(encoding="utf-8"))
    if obj.get("type")!="FeatureCollection" or len(obj.get("features",[]))!=1:
        raise ValueError("Expected one EPSG:4326 municipality polygon")
    geom=shape(obj["features"][0]["geometry"])
    if geom.is_empty or not geom.is_valid:raise ValueError("Invalid boundary")
    geom=project_geom(Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform,geom)
    step=25.
    left,bottom,right,top=geom.bounds
    left=math.floor(left/step)*step
    bottom=math.floor(bottom/step)*step
    right=math.ceil(right/step)*step
    top=math.ceil(top/step)*step
    width=int(round((right-left)/step))
    height=int(round((top-bottom)/step))
    if width*height>40000000:raise ValueError("Unreasonable grid dimensions")
    trans=Affine(step,0,left,0,-step,top)
    classes=defaultdict(Bivariate)
    regions=defaultdict(Bivariate)
    overall=Bivariate()
    excluded=defaultdict(int)
    with ExitStack() as stack:
        biom={}
        for year in YEARS:
            src=stack.enter_context(rasterio.open(getattr(args,"biomass_"+year)))
            expected_crs=3021 if year=="2010" else 3006
            target_res=25 if year=="2010" else 12.5 if year=="2015" else 10
            if src.crs is None or not matches_expected_crs(src.crs,expected_crs) or src.count!=1 or src.nodata is None:
                raise ValueError("Invalid biomass source metadata "+year)
            if abs(src.res[0]-target_res)>.1:raise ValueError("Unexpected biomass source resolution "+year)
            biom[year]=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=trans,
                width=width,height=height,resampling=Resampling.average,
                src_nodata=src.nodata,nodata=-9999,dtype="float32"))
        src=stack.enter_context(rasterio.open(args.volume_2010))
        if src.crs is None or not matches_expected_crs(src.crs,3021) or src.count!=1 or src.nodata is None:
            raise ValueError("Invalid 2010 volume source CRS/NoData")
        if abs(src.res[0]-25)>.1:raise ValueError("Unexpected 2010 volume source resolution")
        volume=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=trans,
            width=width,height=height,resampling=Resampling.average,
            src_nodata=src.nodata,nodata=-9999,dtype="float32"))
        src=stack.enter_context(rasterio.open(args.nmd))
        if src.crs is None or not matches_expected_crs(src.crs,3006) or src.count!=1:
            raise ValueError("Invalid NMD2018 source CRS")
        if any(abs(abs(v)-10)>.01 for v in src.res):raise ValueError("NMD source is not 10m")
        nmd=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",transform=trans,
            width=width,height=height,resampling=Resampling.nearest,
            src_nodata=src.nodata,nodata=255,dtype="uint8"))
        for row in range(0,height,256):
            for col in range(0,width,256):
                w=Window(col,row,min(256,width-col),min(256,height-row))
                inside=geometry_mask([mapping(geom)],out_shape=(int(w.height),int(w.width)),
                    transform=rasterio.windows.transform(w,trans),invert=True,all_touched=False)
                if not inside.any():continue
                bm={year:np.ma.asarray(biom[year].read(1,window=w,masked=True)).filled(np.nan).astype("float64")
                    for year in YEARS}
                vol=np.ma.asarray(volume.read(1,window=w,masked=True)).filled(np.nan).astype("float64")
                nc=nmd.read(1,window=w,masked=True)
                eligible=inside.copy()
                for year in YEARS:eligible &= np.isfinite(bm[year]) & (bm[year]>=0)
                excluded["valid_biomass_all_years"]+=int(eligible.sum())
                eligible &= np.isfinite(vol) & (vol>=0)
                excluded["valid_biomass_and_volume"]+=int(eligible.sum())
                eligible &= ~np.ma.getmaskarray(nc) & (nc.data!=255)
                if not eligible.any():continue
                excluded["valid_biomass_volume_nmd"]+=int(eligible.sum())
                overall.add(vol[eligible],bm["2010"][eligible])
                for cls in np.unique(nc.data[eligible]):
                    selected=eligible & (nc.data==cls)
                    classes[str(int(cls))].add(vol[selected],bm["2010"][selected])
                # 10x10km geographical tiles, defined explicitly in EPSG:3006.
                ys,xs=np.nonzero(eligible)
                easts=left+(col+xs+.5)*step
                norths=top-(row+ys+.5)*step
                cells=np.column_stack((np.floor(easts/10000).astype("int64"),
                                       np.floor(norths/10000).astype("int64")))
                code=nc.data[ys,xs]
                vx=vol[ys,xs]
                by=bm["2010"][ys,xs]
                for key in np.unique(cells,axis=0):
                    loc=(cells[:,0]==key[0])&(cells[:,1]==key[1])
                    for name in ("Vatten NMD2018","Skog NMD2018","Ovrig mark NMD2018"):
                        mask=loc & np.array([landgroup(int(c))==name for c in code],dtype=bool)
                        if mask.any():regions[(int(key[0]),int(key[1]),name)].add(vx[mask],by[mask])
    all_result=overall.result()
    class_rows=[{"class_code":int(code),"nmd2018_group":landgroup(int(code)),**obj.result()} for code,obj in classes.items()]
    class_rows.sort(key=lambda x:x["class_code"])
    group_summary=defaultdict(Bivariate)
    # Aggregate exactly by replaying sufficient moments without reducing precision.
    for code,b in classes.items():
        dest=group_summary[landgroup(int(code))]
        for field in Bivariate.__slots__:setattr(dest,field,getattr(dest,field)+getattr(b,field))
    group_rows=[{"group":name,**summary.result()} for name,summary in sorted(group_summary.items())]
    region_rows=[{"tile_east_10km":e,"tile_north_10km":n,"group":name,**b.result()}
        for (e,n,name),b in regions.items()]
    region_rows.sort(key=lambda x:(x["tile_north_10km"],x["tile_east_10km"],x["group"]))
    if sum(r["cells"] for r in class_rows)!=all_result["cells"]:raise ValueError("Class count mismatch")
    if sum(r["cells"] for r in group_rows)!=all_result["cells"]:raise ValueError("Group count mismatch")
    if sum(r["cells"] for r in region_rows)!=all_result["cells"]:raise ValueError("Geographic cell count mismatch")
    out={"status":"EXPLORATORY_RAW_2010_BIOMASS_VOLUME_RELATIONSHIP",
      "created_utc":datetime.now(timezone.utc).isoformat(),
      "analysis_CRS":"EPSG:3006","resolution_m":25,"geographic_tile_size_m":10000,
      "population":"Only 2010,2015,2018 matched nonnegative biomass + valid 2010 volume + valid NMD2018 classification within municipal boundary",
      "method":"Full raster warp to 25m EPSG:3006. Population Pearson correlation, ordinary least squares biomass_2010=a+b*volume_2010, coefficient of determination, RMSE, ratio for volume>=10. No biomass conversion.",
      "overall":all_result,"nmd_groups":group_rows,"nmd_classes":class_rows,
      "geographic_tiles_by_group":region_rows,"excluded_counts":dict(excluded),
      "limitations":["2010 biomass and 2010 volume may share model inputs: correlation cannot validate either independently",
                     "2018 landcover is not historical 2010 landcover",
                     "Bivariate OLS is descriptive, not proof of linear physical mass-volume equivalence",
                     "Original units and biomass compartments between years have not been harmonized",
                     "Source raster resampling to aligned 25m pixels can influence boundary values",
                     "Cross-year common-valid footprint and known 2010 volume values may select specific landscapes"]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Overall 2010 relation",json.dumps(all_result,ensure_ascii=False))
    print("2010 relation by broad NMD2018 group",json.dumps(group_rows,ensure_ascii=False))
    print("2010 relation by 25 NMD classes",json.dumps(class_rows,ensure_ascii=False))
    print("10km tile records",len(region_rows))
    print("Reference population",json.dumps(dict(excluded),ensure_ascii=False))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for year in YEARS:p.add_argument("--biomass-"+year,type=Path,required=True)
    p.add_argument("--volume-2010",type=Path,required=True)
    p.add_argument("--nmd",type=Path,required=True)
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--output",type=Path,default=Path("metadata/biomass_volume_2010_cellwise.json"))
    run(p.parse_args())
