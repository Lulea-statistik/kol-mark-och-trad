#!/usr/bin/env python3
"""Audit biomass against a local NMD GeoTIFF without deleting or zeroing any cells.

Requires explicit confirmed NMD class codes; no automatic assumption about
classes or dates. Cross-tabulation is computed at native biomass pixel scale,
with categorical NMD reprojected using nearest-neighbour to that grid.
"""
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds
from shapely.geometry import shape,mapping
from shapely.ops import transform as shp_transform
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
CHUNK=512

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--biomass",required=True,help="Local original biomass GeoTIFF")
    p.add_argument("--nmd",required=True,help="Local NMD2018 basskikt GeoTIFF")
    p.add_argument("--classes",required=True,help="JSON class code map: {water:[...], built:[...], road:[...], review:[...]}")
    p.add_argument("--output",default="metadata/biomass_landcover_audit.json")
    args=p.parse_args()
    codes=json.loads(Path(args.classes).read_text(encoding="utf-8"))
    if not codes or not all(isinstance(v,list) and v and all(isinstance(c,int) for c in v) for v in codes.values()):
        raise ValueError("Class map must contain verified nonempty integer lists")
    if len(set(sum(codes.values(),[])))!=sum(map(len,codes.values())):
        raise ValueError("Class categories overlap")
    fc=json.loads((ROOT/"docs/data/lulea_boundary.geojson").read_text(encoding="utf-8"))
    if fc["crs"]["properties"]["name"]!="EPSG:4326":
        raise ValueError("Unexpected boundary CRS")
    polygon=shape(fc["features"][0]["geometry"])
    out={"audited_at_utc":datetime.now(timezone.utc).isoformat(),"biomass":args.biomass,
         "nmd":args.nmd,"classes":codes,"boundary_status":"working geometry not official",
         "note":"Diagnostic only: no data replaced, no exclusion applied, no ton TS totals.",
         "results":{k:{"pixel_count":0,"biomass_positive_pixels":0,"raw_positive_sum":0.0} for k in codes}}
    with rasterio.open(args.biomass) as src, rasterio.open(args.nmd) as lc:
        if not src.crs or not lc.crs or not src.crs.is_projected or not lc.crs.is_projected:
            raise ValueError("Missing or nonprojected CRS")
        out.update(biomass_crs=str(src.crs),nmd_crs=str(lc.crs),
                   source_resolution=[abs(src.transform.a),abs(src.transform.e)])
        poly=shp_transform(Transformer.from_crs("EPSG:4326",src.crs,always_xy=True).transform,polygon)
        w=from_bounds(*poly.bounds,transform=src.transform).round_offsets().round_lengths()
        w=w.intersection(Window(0,0,src.width,src.height))
        # A WarpedVRT places categorical NMD in the actual original biomass grid,
        # NOT the EPSG:3857 web preview. Nearest prevents invented class values.
        with WarpedVRT(lc,crs=src.crs,transform=src.transform,width=src.width,height=src.height,
                       resampling=Resampling.nearest) as nmd:
            for row in range(int(w.row_off),int(w.row_off+w.height),CHUNK):
                for col in range(int(w.col_off),int(w.col_off+w.width),CHUNK):
                    tile=Window(col,row,min(CHUNK,int(w.col_off+w.width)-col),
                                min(CHUNK,int(w.row_off+w.height)-row))
                    b=src.read(1,window=tile,masked=True)
                    l=nmd.read(1,window=tile,masked=True)
                    interior=geometry_mask([mapping(poly)],out_shape=b.shape,
                                           transform=src.window_transform(tile),invert=True)
                    valid=interior&~np.ma.getmaskarray(b)&~np.ma.getmaskarray(l)&np.isfinite(b.data)&(b.data>=0)
                    for name,classes in codes.items():
                        hit=valid&np.isin(l.data,classes)
                        pos=hit&(b.data>0)
                        rec=out["results"][name]
                        rec["pixel_count"]+=int(np.count_nonzero(hit))
                        rec["biomass_positive_pixels"]+=int(np.count_nonzero(pos))
                        rec["raw_positive_sum"]+=float(np.sum(b.data[pos],dtype="float64"))
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out["results"],ensure_ascii=False,indent=2))
if __name__=="__main__":main()
