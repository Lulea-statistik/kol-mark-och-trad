#!/usr/bin/env python3
"""Read source GeoTIFFs in native CRS and audit values (no conversions or mutation)."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.features import geometry_mask
from shapely.geometry import shape, mapping
from shapely.ops import transform as shp_transform
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "metadata/biomass_native_audit.json"
URLS = {
    "2010": "https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/BIOMASS_XX_P_10.tif",
    "2015": "https://gis.slu.se/data/slu_forest_map/2015/data/Biomass_leaf.tif",
    "2018": "https://gis.slu.se/data/slu_skogliga_grunddata/SGD2/data/SGD2_BIO.tif",
}
ENV = {"GDAL_DISABLE_READDIR_ON_OPEN":"EMPTY_DIR", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS":".tif",
       "GDAL_HTTP_MAX_RETRY":"2","GDAL_HTTP_RETRY_DELAY":"2","GDAL_HTTP_TIMEOUT":"60"}
CHUNK = 512

def audit(url, boundary):
    result = {"url": url, "status": "failed", "physical_units_verified": False,
              "source_values_modified": False}
    with rasterio.Env(**ENV), rasterio.open("/vsicurl/" + url) as ds:
        if not ds.crs or not ds.crs.is_projected:
            raise ValueError("Missing or non-projected source CRS")
        poly = shp_transform(Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True).transform, boundary)
        xmin, ymin, xmax, ymax = poly.bounds
        window = from_bounds(xmin,ymin,xmax,ymax,transform=ds.transform).round_offsets().round_lengths()
        window = window.intersection(Window(0,0,ds.width,ds.height))
        result.update(crs=str(ds.crs), epsg=ds.crs.to_epsg(), resolution=[abs(ds.transform.a),abs(ds.transform.e)],
                      nodata=ds.nodata, scale=ds.scales[0], offset=ds.offsets[0],
                      unit_tag=ds.units[0] if ds.units else None, dtype=ds.dtypes[0],
                      band_tags=ds.tags(1), tags=ds.tags(), description=ds.descriptions[0],
                      native_window=[int(window.col_off),int(window.row_off),int(window.width),int(window.height)])
        n=positive=zero=negative=0
        minval=float("inf");maxval=float("-inf")
        bins={"lt0":0,"0":0,"0to200":0,"200to500":0,"500to1000":0,"gt1000":0}
        examples=[]
        for row in range(int(window.row_off),int(window.row_off+window.height),CHUNK):
            for col in range(int(window.col_off),int(window.col_off+window.width),CHUNK):
                w=Window(col,row,min(CHUNK,int(window.col_off+window.width)-col),min(CHUNK,int(window.row_off+window.height)-row))
                data=ds.read(1,window=w,masked=True)
                inside=geometry_mask([mapping(poly)],out_shape=data.shape,transform=ds.window_transform(w),invert=True)
                good=inside & ~np.ma.getmaskarray(data) & np.isfinite(data.data)
                values=data.data[good].astype("float64")
                if not len(values):continue
                n+=len(values);positive+=int(np.sum(values>0));zero+=int(np.sum(values==0));negative+=int(np.sum(values<0))
                minval=min(minval,float(values.min()));maxval=max(maxval,float(values.max()))
                bins["lt0"]+=int(np.sum(values<0));bins["0"]+=int(np.sum(values==0))
                bins["0to200"]+=int(np.sum((values>0)&(values<=200)))
                bins["200to500"]+=int(np.sum((values>200)&(values<=500)))
                bins["500to1000"]+=int(np.sum((values>500)&(values<=1000)))
                bins["gt1000"]+=int(np.sum(values>1000))
                if np.any(values>1000) and len(examples)<20:
                    locs=np.argwhere(good & (data.data>1000))
                    for rr,cc in locs[:20-len(examples)]:
                        x,y=rasterio.transform.xy(ds.window_transform(w),int(rr),int(cc))
                        examples.append({"x":round(x,2),"y":round(y,2),"value":float(data.data[rr,cc])})
        if n==0:raise ValueError("No valid source pixels inside working boundary")
        result.update(status="native_values_audited",native_pixel_count=n,positive_count=positive,zero_count=zero,
                      negative_count=negative,min_raw=minval,max_raw=maxval,value_bins=bins,
                      extreme_values_sample=examples,
                      warning="Native pixels audited, but numeric unit/scale requires documented product verification. No biomass totals computed.")
    return result

def main():
    fc=json.loads((ROOT/"docs/data/lulea_boundary.geojson").read_text(encoding="utf-8"))
    if fc.get("crs",{}).get("properties",{}).get("name")!="EPSG:4326":
        raise ValueError("Working polygon CRS not EPSG:4326")
    boundary=shape(fc["features"][0]["geometry"])
    payload={"checked_utc":datetime.now(timezone.utc).isoformat(),
             "boundary":"docs/data/lulea_boundary.geojson", "boundary_crs":"EPSG:4326",
             "boundary_quality":"working geometry, not official boundary",
             "entries":{}}
    for year,url in URLS.items():
        try: payload["entries"][year]=audit(url,boundary)
        except Exception as exc:payload["entries"][year]={"url":url,"status":"failed","error":str(exc)[:700]}
        print(year,payload["entries"][year]["status"],flush=True)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if all(v["status"]!="native_values_audited" for v in payload["entries"].values()):
        raise SystemExit("No native source raster could be verified. Check artifact.")
if __name__=="__main__":main()
