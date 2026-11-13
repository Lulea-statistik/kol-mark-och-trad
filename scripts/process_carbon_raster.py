#!/usr/bin/env python3
"""Build one verified Lulea carbon raster overlay.

Source is NEVER inferred from file name; caller must declare physical units.
Crop/mask in the source raster CRS, sum on a separately reprojected EPSG:3006
metric grid, and fully reproject the data grid to EPSG:3857 for Leaflet.
No geopandas, synthetic values, or polygon-bound-only raster positioning.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling, transform_bounds
from shapely.geometry import shape, mapping
from shapely.ops import transform as shapely_transform
from pyproj import Transformer
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'/'data'
BOUNDARY=OUT/'lulea_boundary.geojson'
INVALID=-9999.0

def convert(values,units,dry_per_m3):
    if units=='tonnes_C_per_ha':return values
    if units=='tonnes_dry_per_ha':return values*0.5
    if units=='kg_dry_per_ha':return values*0.0005
    if units=='m3sk_per_ha':
        if dry_per_m3 is None or not 0<dry_per_m3<2:
            raise ValueError('Volym kräver ett uttryckligt validerat --tonnes-dry-per-m3sk')
        return values*dry_per_m3*0.5
    raise ValueError('Unsupported physical units')

def warp_grid(values, transform, src_crs, target_crs, max_size=None):
    height,width=values.shape
    left,bottom,right,top=rasterio.transform.array_bounds(height,width,transform)
    dst_transform,dw,dh=calculate_default_transform(src_crs,target_crs,width,height,left,bottom,right,top)
    if max_size and max(dw,dh)>max_size:
        scale=max(dw,dh)/max_size
        dst_transform=dst_transform*rasterio.Affine.scale(scale,scale)
        dw=max(1,int(np.ceil(dw/scale)));dh=max(1,int(np.ceil(dh/scale)))
    dest=np.full((dh,dw),INVALID,dtype='float32')
    reproject(source=values,destination=dest,src_transform=transform,
              src_crs=src_crs,src_nodata=INVALID,dst_transform=dst_transform,
              dst_crs=target_crs,dst_nodata=INVALID,resampling=Resampling.nearest)
    return dest,dst_transform

def rgba(values):
    valid=np.isfinite(values)&(values!=INVALID)&(values>=0)
    image=np.zeros((*values.shape,4),dtype=np.uint8)
    if not valid.any():return image
    # Color limits deliberately based on the declared physical carbon density
    # and robust percentiles, not invented standard thresholds.
    p=float(np.percentile(values[valid],98))
    if p<=0:p=1
    q=np.clip(values[valid]/p,0,1)
    image[valid,0]=np.asarray(250-190*q,dtype='uint8')
    image[valid,1]=np.asarray(238-100*q,dtype='uint8')
    image[valid,2]=np.asarray(192-150*q,dtype='uint8')
    image[valid,3]=215
    return image

def main():
    p=argparse.ArgumentParser()
    p.add_argument('raster',type=Path,help='Local GeoTIFF already downloaded under source terms')
    p.add_argument('--layer',required=True,choices=['biomass','soil','soil_all','volume'])
    p.add_argument('--units',required=True,choices=['tonnes_C_per_ha','tonnes_dry_per_ha','kg_dry_per_ha','m3sk_per_ha'])
    p.add_argument('--source',required=True,help='Institution, exact product and omdrev/version')
    p.add_argument('--source-year',required=True,help='Raster source year/epoch, not dashboard publication year')
    p.add_argument('--tonnes-dry-per-m3sk',type=float,default=None)
    p.add_argument('--calibration',help='Required reference to validated dry mass / m3sk factor for volume')
    args=p.parse_args()
    if args.layer in ('soil','soil_all') and args.units!='tonnes_C_per_ha':
        p.error('Soil maps require a verified tonnes_C_per_ha source unit')
    if args.layer=='volume' and (args.units!='m3sk_per_ha' or not args.calibration):
        p.error('Volume fallback requires m3sk_per_ha and a documented calibration')
    if args.layer=='biomass' and args.units not in ('tonnes_dry_per_ha','kg_dry_per_ha'):
        p.error('Biomass requires dry-mass units; do not silently treat m3sk as biomass')
    feat=json.loads(BOUNDARY.read_text(encoding='utf-8'))['features'][0]
    polygon=shape(feat['geometry'])
    if not polygon.is_valid or polygon.is_empty:raise ValueError('Invalid Lulea working geometry')
    with rasterio.open(args.raster) as src:
        if not src.crs:raise ValueError('Source raster has no verifiable CRS')
        if src.crs.is_geographic and src.crs.to_epsg() not in (4326,4258):
            raise ValueError('Check unsupported geographic source CRS explicitly')
        transformer=Transformer.from_crs('EPSG:4326',src.crs,always_xy=True)
        boundary_src=shapely_transform(transformer.transform,polygon)
        data,tf=mask(src,[mapping(boundary_src)],crop=True,filled=True,nodata=INVALID,indexes=1)
        values=data.astype('float32',copy=False)
        source_valid=np.isfinite(values)&(values!=INVALID)
        if src.nodata is not None:source_valid&=(values!=src.nodata)
        if not source_valid.any():raise ValueError('No valid source pixels inside Lulea')
        if np.any(values[source_valid]<0):raise ValueError('Negative values found: verify nodata and units')
        values[~source_valid]=INVALID
        vals=np.full(values.shape,INVALID,dtype='float32')
        vals[source_valid]=convert(values[source_valid],args.units,args.tonnes_dry_per_m3sk)
        source_crs=str(src.crs)
    # Carbon mass: use a metric EPSG:3006 grid, not latitude/longitude degrees.
    # Source maps with forest coverage naturally leave non-forest cells as NODATA;
    # never infer missing = zero or extrapolate the covered-cell sum to all land.
    area_values,area_tf=warp_grid(vals,tf,source_crs,'EPSG:3006')
    area_valid=np.isfinite(area_values)&(area_values!=INVALID)&(area_values>=0)
    # Warp produces a rectangular bounding box: mask the actual municipal polygon
    # in the EPSG:3006 grid before summing to avoid outside-polygon pixels.
    metric_poly=shapely_transform(Transformer.from_crs('EPSG:4326','EPSG:3006',always_xy=True).transform,polygon)
    from rasterio.features import geometry_mask
    inside=geometry_mask([mapping(metric_poly)],out_shape=area_values.shape,
                         transform=area_tf,invert=True,all_touched=False)
    eligible=area_valid&inside
    pixel_ha=abs(area_tf.a*area_tf.e-area_tf.b*area_tf.d)/10000.0
    covered_hectares=float(np.count_nonzero(eligible)*pixel_ha)
    municipality_hectares=float(metric_poly.area/10000.0)
    coverage_pct=round(min(100.0,100.0*covered_hectares/municipality_hectares),2)
    total=float(np.sum(area_values[eligible].astype('float64'))*pixel_ha)
    # All 3857 map pixels are fully resampled/reprojected from the cropped source
    # grid; transforming only corner coordinates would be wrong.
    web,web_tf=warp_grid(vals,tf,source_crs,'EPSG:3857',max_size=1600)
    web_inside=geometry_mask([mapping(shapely_transform(
        Transformer.from_crs('EPSG:4326','EPSG:3857',always_xy=True).transform,polygon))],
        out_shape=web.shape,transform=web_tf,invert=True,all_touched=False)
    web[~web_inside]=INVALID
    OUT.mkdir(parents=True,exist_ok=True)
    filename=args.layer+'.png'
    Image.fromarray(rgba(web),'RGBA').save(OUT/filename,optimize=True)
    xmin,ymin,xmax,ymax=rasterio.transform.array_bounds(*web.shape,web_tf)
    west,south,east,north=transform_bounds('EPSG:3857','EPSG:4326',xmin,ymin,xmax,ymax)
    meta_file=OUT/'layers.json'
    meta=json.loads(meta_file.read_text(encoding='utf-8'))
    meta['layers'][args.layer]={
        'image':'data/'+filename,
        'bounds':[[south,west],[north,east]],
        'units':'ton C/ha (modellerad koltäthet)',
        'total_tonnes_C':round(total,1),
        'total_scope':'observed_coverage_within_municipality',
        'covered_hectares':round(covered_hectares,2),
        'municipality_hectares':round(municipality_hectares,2),
        'coverage_pct_of_municipality':coverage_pct,
        'spatial_scope':'Luleå kommun – endast giltiga rasterceller inom kommunpolygonen',
        'source':args.source,'source_year':args.source_year,'source_crs':source_crs,
        'map_crs':'EPSG:3857','aggregation_crs':'EPSG:3006',
        'input_units':args.units,
        'calibration':args.calibration if args.layer=='volume' else None,
        'method':'Originalraster maskat i sitt CRS; omräknat till ton C/ha, area-summerat i SWEREF 99 TM (EPSG:3006), helt rasterreprojicerat till EPSG:3857 för webbvisning. Kommungräns är arbetsgeometri.',
        'coverage_pct_of_municipal_bbox':round(float(100*np.count_nonzero(eligible)/max(1,np.count_nonzero(inside))),1)}
    meta_file.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(args.layer,source_crs,'t C=',round(total,1),'pixels=',int(eligible.sum()))
if __name__=='__main__':main()
