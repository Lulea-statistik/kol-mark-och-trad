#!/usr/bin/env python3
"""Local licensed SMD2000 versus native 2010 biomass and NMD2018.

Run only with a user-provided SMD vector; never upload the licensed source
dataset to a public repository. Native 2010 raster pixels remain unchanged.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fiona
import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.features import rasterize, geometry_mask
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from scipy.ndimage import binary_dilation
from shapely.geometry import shape, mapping
from shapely.ops import transform as geom_transform
from audit_native_2010_water_fraction_mask import render_native_fraction
from fetch_and_compare_biomass_native import matches_expected_crs

SMD_WATER={80,81,82,83,84,85,86}
SMD_FOREST={40,41,43,44,45,46,47,48,49}
NMD_FOREST=set(range(111,118))|set(range(121,128))

def code_group(code):
    if code in SMD_WATER:return 'SMD2000_water'
    if code in SMD_FOREST:return 'SMD2000_forest'
    if code==0:return 'SMD2000_no_polygon'
    return 'SMD2000_other'

def rasterize_smd(path, source_epsg, destination):
    with fiona.open(path) as src:
        explicit=src.crs_wkt or src.crs
        if explicit:
            crs=CRS.from_user_input(explicit)
            if source_epsg is not None and not crs.equals(CRS.from_epsg(source_epsg)):
                raise ValueError('SMD .prj contradicts supplied EPSG')
        elif source_epsg is not None:
            crs=CRS.from_epsg(source_epsg)
        else:
            raise ValueError('SMD .prj missing; verify and supply --smd-epsg')
        tx=Transformer.from_crs(crs,destination.crs,always_xy=True).transform
        if 'GRIDCODE' not in src.schema['properties']:raise ValueError('Missing SMD GRIDCODE')
        features=[]
        codes=Counter()
        for item in src:
            code=int(item['properties']['GRIDCODE'])
            polygon=shape(item['geometry'])
            if polygon.is_empty:continue
            if not polygon.is_valid:raise ValueError('Invalid SMD polygon '+str(item['id']))
            features.append((mapping(geom_transform(tx,polygon)),code))
            codes[code]+=1
    arr=rasterize(features,out_shape=(destination.height,destination.width),
                  transform=destination.transform,all_touched=False,fill=0,dtype='uint8')
    return arr,crs,len(features),codes

def main(args):
    fc=json.loads(args.boundary.read_text(encoding='utf-8'))
    if fc.get('type')!='FeatureCollection' or len(fc.get('features',[]))!=1:
        raise ValueError('Expected one municipality polygon in EPSG:4326')
    border=shape(fc['features'][0]['geometry'])
    if border.is_empty or not border.is_valid:raise ValueError('Invalid boundary')
    with ExitStack() as stack:
        b=stack.enter_context(rasterio.open(args.biomass_2010))
        v=stack.enter_context(rasterio.open(args.volume_2010))
        nmd=stack.enter_context(rasterio.open(args.nmd))
        if not matches_expected_crs(b.crs,3021) or not matches_expected_crs(v.crs,3021):
            raise ValueError('2010 source CRS must be verified EPSG:3021')
        if not matches_expected_crs(nmd.crs,3006):raise ValueError('NMD2018 source CRS must be EPSG:3006')
        if (b.transform,b.width,b.height)!=(v.transform,v.width,v.height):
            raise ValueError('Native 2010 biomass and volume grids differ')
        if any(abs(abs(q)-25)>.01 for q in b.res) or any(abs(abs(q)-10)>.01 for q in nmd.res):
            raise ValueError('Unexpected raster source resolution')
        if any(s.nodata is None for s in (b,v,nmd)):raise ValueError('Raster NoData not declared')
        geometry=geom_transform(Transformer.from_crs('EPSG:4326','EPSG:3021',always_xy=True).transform,border)
        smd,crs,npolygons,classes=rasterize_smd(args.smd_shp,args.smd_epsg,b)
        print('Original SMD polygons transformed; calculating 2018 water cover in native 2010 grid',flush=True)
        water,coverage=render_native_fraction(nmd,b.transform,b.width,b.height)
        eligible=coverage>=.999
        pure=eligible & (water>=.999)
        nonpure=eligible & ~pure
        four=binary_dilation(nonpure,structure=np.array([[0,1,0],[1,1,1],[0,1,0]],dtype=bool)) & pure
        eight=binary_dilation(nonpure,structure=np.ones((3,3),dtype=bool)) & pure
        out=defaultdict(lambda:{'cells':0,'valid_2010_cells':0,'sum_biomass':0.,'sum_volume':0.,'smd_codes':Counter()})
        isolated=[]
        xform=Transformer.from_crs('EPSG:3021','EPSG:3006',always_xy=True)
        nmdcat=stack.enter_context(WarpedVRT(nmd,crs='EPSG:3021',transform=b.transform,width=b.width,
                     height=b.height,resampling=Resampling.nearest,src_nodata=nmd.nodata,nodata=255,dtype='uint8'))
        for row in range(0,b.height,256):
            for col in range(0,b.width,256):
                win=Window(col,row,min(256,b.width-col),min(256,b.height-row))
                h,w=int(win.height),int(win.width)
                local=geometry_mask([mapping(geometry)],out_shape=(h,w),
                    transform=rasterio.windows.transform(win,b.transform),invert=True,all_touched=False)
                if not local.any():continue
                rr=slice(row,row+h);cc=slice(col,col+w)
                local &= eligible[rr,cc]
                if not local.any():continue
                m=b.read(1,window=win,masked=True)
                z=v.read(1,window=win,masked=True)
                n=nmdcat.read(1,window=win,masked=True)
                valid=~np.ma.getmaskarray(m)&~np.ma.getmaskarray(z)&np.isfinite(m.data)&np.isfinite(z.data)&(m.data>=0)&(z.data>=0)
                s=smd[rr,cc]
                sw=np.isin(s,list(SMD_WATER))
                sf=np.isin(s,list(SMD_FOREST))
                nf=(~np.ma.getmaskarray(n))&np.isin(n.data,list(NMD_FOREST))
                localpure=local & pure[rr,cc]
                masks={
                    'NMD2018_full_water':localpure,
                    'NMD2018_full_water_side_land':localpure&four[rr,cc],
                    'NMD2018_full_water_diagonal_land_only':localpure&eight[rr,cc]&~four[rr,cc],
                    'NMD2018_full_water_no_8_land':localpure&~eight[rr,cc],
                    'SMD2000_water_and_NMD2018_full_water':localpure&sw,
                    'SMD2000_forest_and_NMD2018_full_water':localpure&sf,
                    'SMD2000_other_and_NMD2018_full_water':localpure&~sw&~sf&(s!=0),
                    'SMD2000_forest_and_NMD2018_forest':local&sf&nf,
                    'SMD2000_water_and_NMD2018_forest':local&sw&nf,
                    'SMD2000_forest_and_NMD2018_any_water':local&sf&(water[rr,cc]>.001)
                }
                for name,selection in masks.items():
                    target=out[name]
                    target['cells']+=int(selection.sum())
                    ok=selection&valid
                    target['valid_2010_cells']+=int(ok.sum())
                    target['sum_biomass']+=float(np.sum(m.data[ok],dtype=np.float64))
                    target['sum_volume']+=float(np.sum(z.data[ok],dtype=np.float64))
                    vals,cnts=np.unique(s[ok],return_counts=True)
                    target['smd_codes'].update({int(a):int(t) for a,t in zip(vals,cnts)})
                critical=masks['NMD2018_full_water_no_8_land']&valid
                cy,cx=np.nonzero(critical)
                for r,c in zip(cy,cx):
                    east,north=b.transform*(col+int(c)+.5,row+int(r)+.5)
                    e3006,n3006=xform.transform(east,north)
                    isolated.append({
                       'easting_epsg3021':float(east),'northing_epsg3021':float(north),
                       'easting_epsg3006':float(e3006),'northing_epsg3006':float(n3006),
                       'smd2000_code':int(s[r,c]),'smd2000_group':code_group(int(s[r,c])),
                       'biomass2010_raw':float(m.data[r,c]),'volume2010_raw':float(z.data[r,c])
                    })
        summary={}
        for name,d in out.items():
            count=d['valid_2010_cells']
            summary[name]={
              'cells':d['cells'],'valid_biomass_and_volume_2010_cells':count,
              'valid_2010_percent':100*count/d['cells'] if d['cells'] else None,
              'mean_biomass_2010_raw_valid':d['sum_biomass']/count if count else None,
              'mean_volume_2010_raw_valid':d['sum_volume']/count if count else None,
              'smd_class_codes_among_valid':dict(sorted(d['smd_codes'].items()))
            }
        if summary['NMD2018_full_water_no_8_land']['valid_biomass_and_volume_2010_cells']!=len(isolated):
            raise ValueError('Isolated cell summary does not match extracted coordinates')
        result={
          'created_utc':datetime.now(timezone.utc).isoformat(),
          'analysis_crs':'EPSG:3021','smd_crs':crs.to_string(),
          'smd_reference_year':2000,'smd_polygons':npolygons,'smd_class_polygon_counts':dict(sorted(classes.items())),
          'summary':summary,'isolated_NMD2018_water_2010_native_cells':isolated,
          'method':'SMD vector transformed and center-point rasterized to unchanged native 2010 EPSG:3021 25m grid; original NMD2018 10m binary water/coverage reprojected by area average.',
          'limitations':['SMD2000 is GENERALIZED 1/2/5/25ha polygon data, NOT original 25m pixel source',
                         'SMD 2000 and NMD 2018 cannot establish actual land cover in 2010',
                         'SMD source may have imperfect classifications or generalized coastlines',
                         'Only source clip native-grid cells are analyzed, original national model mask is unknown',
                         'No raw SMD polygons are included in outputs; review licensing before wider dissemination']
        }
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Summary SMD2000 versus native biomass 2010:',json.dumps(summary,ensure_ascii=False),flush=True)
        print('Critical completely water-classified 2010 cells:',len(isolated),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--smd-shp',type=Path,required=True)
    p.add_argument('--smd-epsg',type=int,help='Only for SMD without .prj; verify separately')
    p.add_argument('--biomass-2010',type=Path,required=True)
    p.add_argument('--volume-2010',type=Path,required=True)
    p.add_argument('--nmd',type=Path,required=True)
    p.add_argument('--boundary',type=Path,default=Path('docs/data/lulea_boundary.geojson'))
    p.add_argument('--output',type=Path,default=Path('metadata/smd2000_vs_native_2010_private.json'))
    main(p.parse_args())
