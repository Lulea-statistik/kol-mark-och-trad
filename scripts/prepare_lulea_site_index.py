#!/usr/bin/env python3
"""QA and harmonize downloaded pine/spruce site-index rasters for Lulea.

Inputs are local, licence-permitted GeoTIFFs. Never download/redistribute raw
Skogsstyrelsen data. The reference grid MUST already be clipped to Lulea,
25 m EPSG:3006. No bonitet or biomass is inferred from H100 alone.
"""
from __future__ import annotations
import argparse,json,math,hashlib
from pathlib import Path
from contextlib import ExitStack
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

AGES=((20,40),(40,60),(60,80),(80,100),(100,140),(140,math.inf))

def summarize(a):
    for name in ("pine","spruce","grid","forest_mask"):
        if not getattr(a,name).is_file():
            raise FileNotFoundError(f"{name}: {getattr(a,name)}")
    with ExitStack() as stack:
        grid=stack.enter_context(rasterio.open(a.grid))
        if grid.crs is None or grid.crs.to_epsg()!=3006:
            raise ValueError("Reference-grid CRS must be EPSG:3006, verified from file")
        if not (abs(grid.res[0]-25)<1e-8 and abs(grid.res[1]-25)<1e-8):
            raise ValueError("Reference grid must be 25 x 25 m")
        if not grid.transform.is_rectilinear:
            raise ValueError("Rotated reference grid is unsupported")
        mask=stack.enter_context(rasterio.open(a.forest_mask))
        pine=stack.enter_context(rasterio.open(a.pine))
        spruce=stack.enter_context(rasterio.open(a.spruce))
        if any(src.crs is None for src in (mask,pine,spruce)):
            raise ValueError("Source CRS missing: do not assume EPSG:3006")
        age=stack.enter_context(rasterio.open(a.age)) if a.age else None
        if age and age.crs is None:
            raise ValueError("Age raster CRS missing")
        kwargs=dict(crs=grid.crs, transform=grid.transform,
                    width=grid.width,height=grid.height)
        si_vrt={}
        for kind,src in (("pine",pine),("spruce",spruce)):
            si_vrt[kind]=stack.enter_context(WarpedVRT(src,**kwargs,
                resampling=Resampling.bilinear,nodata=-9999))
        forest=stack.enter_context(WarpedVRT(mask,**kwargs,
                resampling=Resampling.nearest,nodata=0))
        age_vrt=(stack.enter_context(WarpedVRT(age,**kwargs,
                resampling=Resampling.nearest,nodata=-9999)) if age else None)
        # Forest mask is explicitly 1=include. Do not silently treat every
        # nonzero NMD land-cover code as forest.
        data={kind:[] for kind in ("pine","spruce")}
        by_age={label:{kind:[] for kind in data}
                for label in ("20-39","40-59","60-79","80-99","100-139","140+")}
        counted_mask=0
        for _,window in grid.block_windows(1):
            fm=forest.read(1,window=window,masked=True)
            valid=(~np.ma.getmaskarray(fm))&(fm.data==a.forest_value)
            counted_mask+=int(valid.sum())
            ag=age_vrt.read(1,window=window,masked=True) if age_vrt else None
            for kind in data:
                z=si_vrt[kind].read(1,window=window,masked=True)
                raw=z.data.astype("float64")*a.si_scale
                ok=valid&(~np.ma.getmaskarray(z))&np.isfinite(raw)&(raw>=a.min_si)&(raw<=a.max_si)
                data[kind].extend(raw[ok].tolist())
                if ag is not None:
                    aa=ag.data
                    ok &= (~np.ma.getmaskarray(ag))&np.isfinite(aa)
                    for label,(low,high) in zip(by_age,AGES):
                        by_age[label][kind].extend(raw[ok&(aa>=low)&(aa<high)].tolist())
        def stats(numbers):
            if not numbers:return {"cells":0,"area_ha":0}
            z=np.asarray(numbers,dtype="float64")
            return {"cells":int(z.size),"area_ha":float(z.size*.0625),
              "mean_H100_m":float(z.mean()),"median_H100_m":float(np.median(z)),
              "p10_H100_m":float(np.percentile(z,10)),
              "p90_H100_m":float(np.percentile(z,90))}
        return {
           "status":"LOCAL_SITE_INDEX_H100_QA_NOT_BONITET_NOT_BIOMASSA",
           "analysis_crs":"EPSG:3006","analysis_cell_m":25,
           "source_crs":{k:str(v.crs) for k,v in (("pine",pine),("spruce",spruce),("forest",mask))},
           "source_files":{k:Path(v.name).name for k,v in (("pine",pine),("spruce",spruce))},
           "site_index_units":"H100 metres, user-confirmed scale factor",
           "si_scale":a.si_scale,"si_valid_range_H100_m":[a.min_si,a.max_si],
           "forest_mask_pixels":counted_mask,"forest_value":a.forest_value,
           "forest_mask_caveat":"Reference grid must be Lulea-clipped. User-supplied 1/0 mask is NOT raw NMD class codes.",
           "species":{kind:stats(data[kind]) for kind in data},
           "by_2010_age_bin":{key:{species:stats(values) for species,values in val.items()}
               for key,val in by_age.items()} if age else None,
           "further_work":"Verify download rights, full 2025 SI method, units and conversions for Norrbotten species and vegetation before a bonitet/biomass model is built."
        }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pine",required=True,type=Path)
    p.add_argument("--spruce",required=True,type=Path)
    p.add_argument("--grid",required=True,type=Path,help="Lulea-clipped EPSG:3006 25m reference raster")
    p.add_argument("--forest-mask",required=True,type=Path,help="Binary 1/0 forest mask; NOT raw NMD codes")
    p.add_argument("--forest-value",type=int,default=1)
    p.add_argument("--age",type=Path,help="Optional 2010 forest age raster, CRS checked")
    p.add_argument("--si-scale",type=float,default=1.,help="Explicit conversion from stored values to metres")
    p.add_argument("--min-si",type=float,default=5.)
    p.add_argument("--max-si",type=float,default=45.)
    p.add_argument("--output",type=Path,default=Path("metadata/lulea_site_index_qa.json"))
    a=p.parse_args()
    if a.si_scale<=0 or a.min_si>=a.max_si: p.error("Invalid SI scale/range")
    result=summarize(a)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("SITE_INDEX_QA",[(key,round(value.get("median_H100_m",0),2),value["cells"])
        for key,value in result["species"].items()])
if __name__=="__main__":main()
