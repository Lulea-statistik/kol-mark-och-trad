#!/usr/bin/env python3
"""Inspect two authorized Skogsstyrelsen SIS ZIP archives offline.

Never downloads or republishes archives. Finds embedded rasters and validates
source raster CRS/NoData/resolution before a Lulea analysis is attempted.
Untrusted ZIP members are not extracted. This does NOT infer bonitet from SIS.
"""
from __future__ import annotations
import argparse,json,zipfile,tempfile
from pathlib import Path
from collections import Counter
import rasterio

RASTER_SUFFIXES={".tif",".tiff",".img",".vrt"}
def audit(archive:Path,expected:str):
    if not archive.is_file() or not zipfile.is_zipfile(archive):
        raise ValueError(f"{archive}: missing or invalid ZIP archive")
    with zipfile.ZipFile(archive) as z:
        members=[m for m in z.infolist() if not m.is_dir()]
        if not members: raise ValueError(f"{archive}: ZIP is empty")
        if len(members)>2000: raise ValueError("Unusually many archive members")
        entries=[]
        for item in members:
            name=Path(item.filename)
            if name.is_absolute() or ".." in name.parts or "\\" in item.filename:
                raise ValueError(f"Unsafe archive entry: {item.filename}")
            entries.append({"name":item.filename,"size_bytes":item.file_size})
        # Rasterio's /vsizip/ support enables TIFF and some IMG reads without
        # unpacking, while preserving expected sidecar files within the ZIP.
        found=[]
        for item in members:
            path=Path(item.filename)
            if path.suffix.lower() not in RASTER_SUFFIXES:continue
            vpath=f"/vsizip/{archive.resolve()}/{item.filename}"
            try:
                with rasterio.open(vpath) as src:
                    if src.crs is None: raise ValueError("Raster source has no CRS")
                    bounds=[float(v) for v in src.bounds]
                    found.append({
                        "entry":item.filename,"driver":src.driver,"width":src.width,"height":src.height,
                        "count":src.count,"crs":str(src.crs),"epsg":src.crs.to_epsg(),
                        "resolution":list(src.res),"nodata":src.nodata,
                        "dtype":src.dtypes[0],"bounds":bounds,
                        "band_description":src.descriptions[0] if src.count else None,
                        "scale":src.scales[0] if src.count else None,
                        "offset":src.offsets[0] if src.count else None
                    })
            except rasterio.errors.RasterioIOError as exc:
                found.append({"entry":item.filename,"read_error":str(exc)[:180]})
        valid=[r for r in found if "read_error" not in r]
        if not valid: raise ValueError(f"{archive}: no readable raster found. Check format and permissions.")
        if any(r["epsg"]!=3006 for r in valid):
            raise ValueError(f"{archive}: CRS mismatched. Read actual metadata, don't assume EPSG3006")
        return {"kind":expected,"archive_filename":archive.name,"members_count":len(members),
                "raster_count":len(valid),"rasters":found,
                "scale_caveat":"GDAL scale/offset are inspected, but SI physical units must be verified in official product documentation.",
                "permission_caveat":"Original ZIP files remain local. Redistribution requires checking Skogsstyrelsen terms."}
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pine-zip",required=True,type=Path)
    parser.add_argument("--spruce-zip",required=True,type=Path)
    parser.add_argument("--output",type=Path,default=Path("metadata/standortsindex_archives_qa.json"))
    args=parser.parse_args()
    data={"status":"SOURCE_RASTER_ARCHIVES_METADATA_ONLY_NOT_BONITET",
          "pine":audit(args.pine_zip,"pine"),"spruce":audit(args.spruce_zip,"spruce"),
          "next_step":"Identify correct main TIFF for each ZIP, confirm SI is H100 metres and use prepare_lulea_site_index.py on authorized local rasters."}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    for species in ("pine","spruce"):
        print(species,[(v["entry"],v.get("epsg"),v.get("resolution")) for v in data[species]["rasters"]])
if __name__=="__main__":main()
