#!/usr/bin/env python3
"""Produce genuinely source-derived, unit-free soil-carbon previews for Lulea.

The preview PNGs are evidence for source raster coverage/values, not carbon
quantification. This never assumes that the source values are t C/ha.
"""
from __future__ import annotations
import json
import gzip
from pathlib import Path
import numpy as np
import rasterio
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds, calculate_default_transform
from rasterio.transform import from_bounds as affine_from_bounds
from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform as transform_geometry
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"metadata"/"lulea_carbon_preview"
SOURCES={
 "biomass":"https://gis.slu.se/data/slu_skogliga_grunddata/SGD2/data/SGD2_BIO.tif",
 "stock_dom":"https://gis.slu.se/data/carbon/2023/Stock_DOM_2023_Lan/DOM_2023_Norrbottens.tif",
 "change_soc":"https://gis.slu.se/data/carbon/2023/Change_SOC_2023_Lan/Change_SOC_2023_Norrbottens.tif",
 "change_dom":"https://gis.slu.se/data/carbon/2023/Change_DOM_2023_Lan/Change_DOM_2023_Norrbottens.tif",
 "change_all":"https://gis.slu.se/data/carbon/2023/Change_All_2023_Lan/Change_All_2023_Norrbottens.tif",
 "soil":"https://gis.slu.se/data/carbon/2023/Stock_SOC_2023_Lan/SOC_2023_Norrbottens.tif",
 "soil_all":"https://gis.slu.se/data/carbon/2023/Stock_All_2023_Lan/Stock_All_2023_Norrbottens.tif",
}
SRC_ENV={"GDAL_DISABLE_READDIR_ON_OPEN":"EMPTY_DIR","CPL_VSIL_CURL_ALLOWED_EXTENSIONS":".tif",
 "GDAL_HTTP_MAX_RETRY":"3","GDAL_HTTP_RETRY_DELAY":"2","GDAL_HTTP_TIMEOUT":"90",
 "VSI_CACHE":"TRUE","VSI_CACHE_SIZE":"33554432"}

def main():
 fc=json.loads((ROOT/"docs/data/lulea_boundary.geojson").read_text(encoding="utf-8"))
 poly=shape(fc["features"][0]["geometry"])
 if not poly.is_valid:raise ValueError("municipal working geometry invalid")
 web_poly=transform_geometry(Transformer.from_crs("EPSG:4326","EPSG:3857",always_xy=True).transform,poly)
 xmin,ymin,xmax,ymax=web_poly.bounds
 # Entire output grid is genuinely reprojected to EPSG:3857 by WarpedVRT.
 # 1200x1200 preview = low resolution, not a replacement for area integrals.
 width=1200
 height=max(1,round(width*(ymax-ymin)/(xmax-xmin)))
 if height>1800:
  height=1800;width=max(1,round(height*(xmax-xmin)/(ymax-ymin)))
 tf=affine_from_bounds(xmin,ymin,xmax,ymax,width,height)
 inside=geometry_mask([mapping(web_poly)],out_shape=(height,width),transform=tf,invert=True)
 OUT.mkdir(parents=True,exist_ok=True)
 result={"scope":"Only Lulea working municipal polygon; visual QC only","map_crs":"EPSG:3857",
   "working_boundary_crs":"EPSG:4326","source_units_verified":False,
   "no_carbon_totals_computed":True,"files":{}}
 for name,url in SOURCES.items():
  rec={"source_url":url,"status":"pending","units_verified":False}
  try:
   with rasterio.Env(**SRC_ENV):
    with rasterio.open("/vsicurl/"+url) as src:
     if not src.crs:raise ValueError("Source CRS missing")
     rec["source_crs"]=str(src.crs)
     rec["source_nodata"]=src.nodata
     rec["source_resolution_m"]=[float(abs(src.transform.a)),float(abs(src.transform.e))]
     rec["source_unit_tag"]=src.units[0] if src.units else None
     rec["source_description"]=src.descriptions[0] if src.descriptions else None
     rec["source_band_scale"]=src.scales[0] if src.scales else None
     rec["source_band_offset"]=src.offsets[0] if src.offsets else None
     with WarpedVRT(src,crs="EPSG:3857",transform=tf,width=width,height=height,
        resampling=Resampling.nearest,nodata=-9999) as vrt:
      arr=vrt.read(1,masked=True)
    a=np.asarray(arr.data)
    mask=np.ma.getmaskarray(arr)
    is_change=name.startswith("change_")
    # Change/flux rasters can contain negative values. Do not censor them.
    valid=inside&(~mask)&np.isfinite(a)&(a!=-9999)
    if not is_change: valid&=(a>=0)
    rec["valid_pixels"]=int(np.count_nonzero(valid))
    rec["product_family"]="SLU/Skogsstyrelsen Skogliga grunddata SGD2" if name=="biomass" else "SLU Kolkartor 2023"
    rec["municipal_preview_pixels"]=int(np.count_nonzero(inside))
    if not np.any(valid):raise ValueError("No valid source pixels within municipality")
    q2,q98=np.percentile(a[valid],[2,98])
    if q98<=q2:q98=q2+1
    scaled=np.clip((a[valid]-q2)/(q98-q2),0,1)
    image=np.zeros((height,width,4),dtype="uint8")
    # Null / NoData: grey only INSIDE Lulea, outside the municipality transparent.
    null_inside=inside&(~valid)
    image[null_inside]=[160,160,160,200]
    # Colour palette: low = red (#ff0000), high = black (#000000).
    # Relative quantiles are layer-specific and NOT physical carbon concentrations.
    if is_change:
     # Signed values: blue = negative, white = zero, red = positive.
     maxabs=max(1e-9,float(np.percentile(np.abs(a[valid]),98)))
     frac=np.clip(a[valid]/maxabs,-1,1)
     red=np.where(frac>=0,255,np.rint(255*(1+frac)))
     green=np.rint(255*(1-np.abs(frac)))
     blue=np.where(frac<=0,255,np.rint(255*(1-frac)))
     image[valid,0]=np.asarray(red,dtype="uint8")
     image[valid,1]=np.asarray(green,dtype="uint8")
     image[valid,2]=np.asarray(blue,dtype="uint8")
     rec["signed_color_scale_max_abs_p98"]=float(maxabs)
     rec["color_scale_type"]="signed_blue_white_red"
    else:
     intensity=np.asarray(np.rint(255*(1-scaled)),dtype="uint8")
     image[valid,0]=intensity
     image[valid,1]=0
     image[valid,2]=0
     rec["color_scale_type"]="red_black"
    image[valid,3]=225
    filename=name+"_preview.png"
    Image.fromarray(image,"RGBA").save(OUT/filename,optimize=True)
    # The clickable data are the TRUE raw source values sampled onto the same
    # fully reprojected 3857 preview grid. No unit conversion is claimed.
    numeric=np.full(a.shape,-9999,dtype="<f4")
    numeric[valid]=a[valid]
    numeric_file=name+"_sampled_values.f32.gz"
    with gzip.open(OUT/numeric_file,"wb",compresslevel=6) as handle:
     handle.write(numeric.tobytes(order="C"))
    hist,bins=np.histogram(a[valid],bins=12)
    rec["numeric_file"]=numeric_file
    rec["raster_grid_width"]=int(width)
    rec["raster_grid_height"]=int(height)
    rec["raster_grid_crs"]="EPSG:3857"
    rec["raster_grid_bounds_m"]=[float(xmin),float(ymin),float(xmax),float(ymax)]
    rec["raster_grid_nodata"]=-9999
    rec["null_inside_pixels"]=int(np.count_nonzero(null_inside))
    rec["raw_pixel_median"]=float(np.median(a[valid]))
    rec["raw_pixel_mean"]=float(np.mean(a[valid].astype("float64")))
    rec["raw_pixel_sum"]=float(np.sum(a[valid].astype("float64"),dtype="float64"))
    rec["raw_pixel_negative_count"]=int(np.count_nonzero(a[valid]<0))
    rec["raw_pixel_positive_count"]=int(np.count_nonzero(a[valid]>0))
    rec["raw_pixel_zero_count"]=int(np.count_nonzero(a[valid]==0))
    rec["raw_pixel_histogram"]={"edges":[float(x) for x in bins],"counts":[int(x) for x in hist]}
    rec["sample_type"]="Source raster resampled nearest-neighbour to EPSG:3857 preview grid; not native 10-m pixel"
    rec["preview_grid_resolution_metres"]=[float(abs(tf.a)),float(abs(tf.e))]
    rec.update({"status":"visual_preview_created","image":filename,
      "raw_pixel_q02":float(q2),"raw_pixel_q98":float(q98),
      "raw_pixel_min":float(np.min(a[valid])),"raw_pixel_max":float(np.max(a[valid])),
      "color_scale":"relative to unconverted source raster quantiles, no physical unit asserted",
      "preview_bounds_4326":list(transform_bounds("EPSG:3857","EPSG:4326",xmin,ymin,xmax,ymax)),
      "no_area_integral":True})
  except Exception as exc:rec.update({"status":"failed","error":str(exc)[:1000]})
  result["files"][name]=rec
  print(name,rec["status"],"pixels",rec.get("valid_pixels",0),flush=True)
 (OUT/"preview_audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 if any(v["status"]!="visual_preview_created" for v in result["files"].values()):
  raise SystemExit("At least one source failed; review preview artifact")
if __name__=="__main__":main()
