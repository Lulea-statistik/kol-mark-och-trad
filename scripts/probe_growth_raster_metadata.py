#!/usr/bin/env python3
"""Inspect remote SG2 age and site-index metadata without assuming source CRS.

Does not download whole 1-3GB national TIFFs. Each source is independently
checked; errors are reported per layer, never interpreted as empty values.
"""
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
import rasterio

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--registry",type=Path,default=ROOT/"metadata/forest_growth_age_site_index_sources.json")
    p.add_argument("--output",type=Path,default=Path("metadata/forest_growth_remote_raster_probe.json"))
    args=p.parse_args()
    records=json.loads(args.registry.read_text(encoding="utf-8"))
    results=[]
    for item in records["sources"]:
        info={"id":item["id"],"url":item["url"],"status":"unverified"}
        try:
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                 CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
                 GDAL_HTTP_MAX_RETRY="2",GDAL_HTTP_TIMEOUT="30"):
                with rasterio.open("/vsicurl/"+item["url"]) as src:
                    if src.count!=1 or src.crs is None:raise ValueError("No single raster band or CRS")
                    info.update(status="metadata_verified",
                        source_crs_wkt=src.crs.to_wkt(),source_epsg=src.crs.to_epsg(),
                        cell_size=[abs(float(x)) for x in src.res],
                        source_nodata=src.nodata,source_scale=src.scales[0],
                        source_offset=src.offsets[0],source_dtype=src.dtypes[0],
                        width=src.width,height=src.height,
                        bounds=list(src.bounds),unit_names=src.units,
                        band_descriptions=src.descriptions)
        except Exception as error:
            info["status"]="source_read_failed"
            info["error"]=str(error)[:900]
            try:
                import urllib.request
                req=urllib.request.Request(item["url"],method="HEAD",headers={"User-Agent":"Lulea-statistik-QA/1.0"})
                with urllib.request.urlopen(req,timeout=20) as resp:
                    info["http_status"]=resp.status
                    info["http_accept_ranges"]=resp.headers.get("Accept-Ranges")
                    info["http_content_length"]=resp.headers.get("Content-Length")
            except Exception as head_error:
                info["http_head_error"]=str(head_error)[:500]
        results.append(info)
        print(json.dumps(info,ensure_ascii=False),flush=True)
    report={"probed_utc":datetime.now(timezone.utc).isoformat(),
            "source_registry":"metadata/forest_growth_age_site_index_sources.json",
            "all_layers_verified":all(r["status"]=="metadata_verified" for r in results),
            "warning":"Metadata read does not verify forest stand ages, SIS semantics or observation periods; inspect product documentation before growth modeling.",
            "layers":results}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"statuses":{r["id"]:r["status"] for r in results}},indent=2),flush=True)
    failures=[r["id"] for r in results if r["status"]!="metadata_verified"]
    if failures:
        raise SystemExit("Metadata NOT verified for: "+", ".join(failures))
if __name__=="__main__":main()
