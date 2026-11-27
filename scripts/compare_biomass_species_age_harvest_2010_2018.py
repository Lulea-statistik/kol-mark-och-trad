#!/usr/bin/env python3
"""Stratify fixed-cell 2010/2015/2018 biomass by 2010 species and age,
separating recorded 2011-2018 harvests. NOT causal growth or model correction.
"""
from __future__ import annotations
import argparse,json,math
from collections import defaultdict
from contextlib import ExitStack
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import rasterize,geometry_mask
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from shapely.geometry import shape,mapping,box
from shapely.ops import transform as geom_transform
from pyproj import Transformer
from fetch_and_compare_biomass_native import crop_source,matches_expected_crs,EXPECTED
from analyze_forest_age_2010 import check_age
from analyze_historic_volume import validate_archive
from verify_biomass_release import run as verify_biomass
from biomass_harvest_overlay import read_harvest

SPECIES=("pine","spruce","deciduous")
FOREST=set(range(111,118))|set(range(121,128))
AGE=((0,20),(20,40),(40,60),(60,80),(80,100),(100,140),(140,500))
YEARS=("2010","2015","2018")
def classify(p,s,d,v):
    """2010 volume model classes; no adding birch to deciduous double-count."""
    a=np.stack([p,s,d])
    total=a.sum(axis=0)
    valid=(np.isfinite(v)&(v>=20)&np.all(np.isfinite(a)&(a>=0),axis=0)&
          (total>=20)&(np.abs(total-v)<=.20*np.maximum(v,1)))
    share=np.divide(a,np.where(total>0,total,1))
    winner=np.argmax(share,axis=0)
    maxshare=np.max(share,axis=0)
    return np.where(~valid,4,np.where(maxshare>=.6,winner,3)).astype("uint8")
def new():
    return {"cells":0,"sum_tTS":{y:0. for y in YEARS},
            "sum_volume_2010":0.,"sum_age_2010":0.,
            "lower_2015_than_2010":0}
def add(x,mask,arrays):
    n=int(mask.sum())
    if not n:return
    x["cells"]+=n
    for y in YEARS:
        x["sum_tTS"][y]+=float(arrays["bio_"+y][mask].sum(dtype="float64"))*.0625
    x["sum_volume_2010"]+=float(arrays["vol"][mask].sum(dtype="float64"))
    x["sum_age_2010"]+=float(arrays["age"][mask].sum(dtype="float64"))
    x["lower_2015_than_2010"]+=int(np.count_nonzero(arrays["bio_2015"][mask]<arrays["bio_2010"][mask]))
def finish(x):
    n=x["cells"]
    values=x["sum_tTS"]
    return {"cells":n,"ha":n*.0625,"ton_TS_by_year":values,
       "mean_tTS_per_ha":{y:values[y]/(n*.0625) if n else None for y in YEARS},
       "2018_vs_2010_model_ratio_percent":(100*(values["2018"]/values["2010"]-1)
                                               if values["2010"]>0 else None),
       "2015_vs_2010_model_ratio_percent":(100*(values["2015"]/values["2010"]-1)
                                               if values["2010"]>0 else None),
       "mean_model_age_2010":x["sum_age_2010"]/n if n else None,
       "mean_model_volume_2010_raw":x["sum_volume_2010"]/n if n else None,
       "share_cells_2015_lower_than_2010":x["lower_2015_than_2010"]/n if n else None,
       "verified_real_biomass_growth_percent":None}
def run(args):
    # Do not silently replace the verified source products with approximate fields.
    validate_archive(args.volume_dir,args.boundary)
    check_age(args.age_dir,args.boundary)
    verify_biomass(argparse.Namespace(directory=args.biomass_dir,output=args.qa))
    boundary_doc=json.loads(args.boundary.read_text(encoding="utf-8"))
    if boundary_doc["crs"]["properties"]["name"]!="EPSG:4326":raise ValueError("Unverified boundary source CRS")
    if len(boundary_doc.get("features",[]))!=1:raise ValueError("Expected one work polygon")
    b=shape(boundary_doc["features"][0]["geometry"])
    if b.is_empty or not b.is_valid:raise ValueError("Invalid boundary")
    g=geom_transform(Transformer.from_crs(4326,3006,always_xy=True).transform,b)
    harvest,harvest_meta=read_harvest(g)
    if not harvest["2011_2015"] and not harvest["2016_2018"]:
        raise ValueError("Cannot establish harvest overlap from source")
    args.species_dir.mkdir(parents=True,exist_ok=True)
    species_paths={}
    for s,key in (("pine","PINEVOL"),("spruce","SPRUCEVOL"),("deciduous","DECIDUOUSVOL")):
        src=f"https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/{key}_XX_P_10.tif"
        dst=args.species_dir/(s+"_2010_source_crs_clip.tif")
        proof={"sources":{}}
        crop_source(src,"2010",b,dst,proof)
        if not matches_expected_crs(rasterio.open(dst).crs,3021):
            raise ValueError("Species source CRS not EPSG3021")
        species_paths[s]=dst
    paths={"bio_"+y:args.biomass_dir/f"lulea_biomass_{y}_source_crs_clip.tif" for y in YEARS}
    paths.update({"vol":args.volume_dir/"lulea_total_volume_2010_source_crs_clip.tif",
      "age":args.age_dir/"lulea_forest_age_2010_source_crs_clip.tif","nmd":args.nmd})
    paths.update(species_paths)
    # Paired historical source estimates: identical per-pixel location after
    # full raster-grid reprojection, not inferred historical landcover.
    EXPECTED["2005"]=(3021,25.0)
    for name,source_key in (("pine_2005","PINEVOL"),("spruce_2005","SPRUCEVOL")):
        source=f"https://gis.slu.se/data/slu_forest_map/2005/Data/Raster/Rt90/{source_key}_XX_P_05.tif"
        dest=args.species_dir/(name+"_source_crs_clip.tif")
        crop_source(source,"2005",b,dest,{"sources":{}})
        paths[name]=dest
    paths["volume_2005"]=args.volume_dir/"lulea_total_volume_2005_source_crs_clip.tif"
    minx,miny,maxx,maxy=g.bounds
    x0=math.floor(minx/25)*25;y0=math.floor(miny/25)*25
    x1=math.ceil(maxx/25)*25;y1=math.ceil(maxy/25)*25
    w=int(round((x1-x0)/25));h=int(round((y1-y0)/25))
    if w*h>40_000_000:raise ValueError("Unreasonable grid")
    tf=Affine(25,0,x0,0,-25,y1)
    buckets=defaultdict(new)
    stable_buckets=defaultdict(new)
    stable_counts=defaultdict(int)
    dominance_matrices=defaultdict(lambda:np.zeros((4,4),dtype="int64"))
    dominance_sensitivity=defaultdict(int)
    total=new()
    strata=("no_recorded_harvest","recorded_harvest")
    masks=("nmd2018_forest","all_common_2010_volume_ge50")
    labels=("pine","spruce","deciduous","mixed","unknown")
    with ExitStack() as stack:
        vrts={}
        for name,path in paths.items():
            src=stack.enter_context(rasterio.open(path))
            epsg=3006 if name in ("bio_2015","bio_2018","nmd") else 3021
            pix=10 if name in ("bio_2018","nmd") else 12.5 if name=="bio_2015" else 25
            if not matches_expected_crs(src.crs,epsg) or src.nodata is None or src.count!=1 or any(abs(abs(d)-pix)>.05 for d in src.res):
                raise ValueError("Source CRS, pixel size, nodata or bands wrong: "+name)
            vrts[name]=stack.enter_context(WarpedVRT(src,crs="EPSG:3006",
                       transform=tf,width=w,height=h,
                       src_nodata=src.nodata,nodata=255 if name=="nmd" else -9999,
                       resampling=Resampling.nearest if name=="nmd" else Resampling.average,
                       dtype="uint8" if name=="nmd" else "float32"))
        for row in range(0,h,256):
            for col in range(0,w,256):
                win=Window(col,row,min(256,w-col),min(256,h-row))
                size=(int(win.height),int(win.width))
                transform=rasterio.windows.transform(win,tf)
                inside=geometry_mask([mapping(g)],out_shape=size,transform=transform,invert=True)
                if not inside.any():continue
                data={key:np.ma.asarray(v.read(1,window=win,masked=True),dtype="float64").filled(np.nan)
                      for key,v in vrts.items()}
                common=inside.copy()
                for key in paths:
                    common &= np.isfinite(data[key])&(data[key]>=0)
                common &= (data["nmd"]!=255)
                if not common.any():continue
                flags=np.zeros(size,dtype="uint8")
                tile=box(*rasterio.windows.bounds(win,tf))
                for period,flag in (("2011_2015",1),("2016_2018",2)):
                    found=[polygon for polygon in harvest[period] if polygon.intersects(tile)]
                    if found:
                        flags |= rasterize(((mapping(p),flag) for p in found),out_shape=size,transform=transform,fill=0,dtype="uint8")
                c=classify(data["pine"],data["spruce"],data["deciduous"],data["vol"])
                # Historical stability is restricted to independently
                # classifiable pine/spruce dominance in BOTH source years.
                # Not a verified absence of actual species changes.
                v05=data["volume_2005"];v10=data["vol"]
                pine05=data["pine_2005"];spruce05=data["spruce_2005"]
                pine10=data["pine"];spruce10=data["spruce"]
                def dominance(p,s,v):
                    ok=np.isfinite(v)&(v>=20)&np.isfinite(p)&(p>=0)&np.isfinite(s)&(s>=0)
                    return np.where(ok & (p>=.6*v),0,np.where(ok & (s>=.6*v),1,2))
                c05=dominance(pine05,spruce05,v05)
                c10=dominance(pine10,spruce10,v10)
                stable=(c05==c10)&(c05<2)
                # Diagnostic classes 0=pine, 1=spruce, 2=neither >=threshold,
                # 3=invalid/low volume. Always compare the same valid raster cells.
                # The historical products are correlated model estimates, not observations.
                def diagnosis(p,s,v,threshold):
                    ok=np.isfinite(p)&(p>=0)&np.isfinite(s)&(s>=0)&np.isfinite(v)&(v>=20)
                    out=np.full(v.shape,3,dtype="uint8")
                    out[ok]=2
                    out[ok & (p>=threshold*v)]=0
                    out[ok & (p<threshold*v) & (s>=threshold*v)]=1
                    return out
                classes_by_threshold={
                    t:(diagnosis(pine05,spruce05,v05,t),
                       diagnosis(pine10,spruce10,v10,t))
                    for t in (.4,.5,.6,.7)}
                add(total,common,data)
                for scope,geo_mask in (
                  ("nmd2018_forest",np.isin(data["nmd"],list(FOREST))),
                  ("all_common_2010_volume_ge50",data["vol"]>=50)):
                    base=common & geo_mask
                    if not base.any():continue
                    for group,flag_mask in (
                     ("no_recorded_harvest",flags==0),
                     ("recorded_harvest",flags>0)):
                        subset=base&flag_mask
                        if not subset.any():continue
                        add(buckets[(scope,group,"all","all")],subset,data)
                        for minimum_age in (20,60,80,100):
                            eligible=subset & (data["age"]>=minimum_age)
                            if not eligible.any():continue
                            for threshold,(from_2005,to_2010) in classes_by_threshold.items():
                                key=(scope,group,minimum_age,str(threshold))
                                pair=(from_2005[eligible].astype("int64")*4+
                                      to_2010[eligible].astype("int64"))
                                dominance_matrices[key]+=np.bincount(pair,minlength=16).reshape(4,4)
                                dominance_sensitivity[key]+=int(eligible.sum())
                        # Fixed NMD2018 forest and no recorded harvest. Stable
                        # pine/spruce labels use a conservative >=60% of total
                        # volume in each historical raster year.
                        for min_age in (20,60,80,100):
                            for label,code in (("stable_pine",0),("stable_spruce",1)):
                                selection=subset & stable & (c10==code) & (data["age"]>=min_age)
                                if selection.any():
                                    add(stable_buckets[(scope,group,label,min_age)],selection,data)
                                    stable_counts[(scope,group,label,min_age)]+=int(selection.sum())
                        for threshold in (20,60,80,100):
                            age_subset=subset&(data["age"]>=threshold)
                            if age_subset.any():
                                add(buckets[(scope,group,"all",f"age_ge{threshold}")],age_subset,data)
                        for cls in range(5):
                            species=subset&(c==cls)
                            if not species.any():continue
                            add(buckets[(scope,group,labels[cls],"all")],species,data)
                            for threshold in (20,60,80,100):
                                older=species&(data["age"]>=threshold)
                                if older.any():
                                    add(buckets[(scope,group,labels[cls],f"age_ge{threshold}")],older,data)
                            for amin,amax in AGE:
                                age_mask=species&(data["age"]>=amin)&(data["age"]<amax)
                                if age_mask.any():
                                    add(buckets[(scope,group,labels[cls],f"{amin}-{amax}")],age_mask,data)
    summary={scope:{
       group:{species:{
           "all_ages":finish(buckets[(scope,group,species,"all")]),
           "age_bins":{f"{amin}-{amax}":finish(buckets[(scope,group,species,f"{amin}-{amax}")]) for amin,amax in AGE}
           } for species in labels}
       for group in strata} for scope in masks}
    for scope in masks:
        for group in strata:
            for y in YEARS:
                parent=buckets[(scope,group,"all","all")]["sum_tTS"][y]
                children=sum(buckets[(scope,group,s,"all")]["sum_tTS"][y] for s in labels)
                if not math.isclose(parent,children,rel_tol=1e-8,abs_tol=.01):
                    raise ValueError("Species mass partition mismatch "+scope+" "+group+" "+y)
            a=buckets[(scope,group,"all","all")]
            if a["cells"]!=sum(buckets[(scope,group,s,"all")]["cells"] for s in labels):
                raise ValueError("Species count partition mismatch")
            for species in labels:
                n=buckets[(scope,group,species,"all")]["cells"]
                in_bins=sum(buckets[(scope,group,species,f"{x}-{y}")]["cells"] for x,y in AGE)
                if n<in_bins:raise ValueError("Overlapping age bins")
    older={scope:{flag:{species:{
       f"age_ge{threshold}":finish(buckets[(scope,flag,species,f"age_ge{threshold}")])
       for threshold in (20,60,80,100)}
       for species in ("all",)+labels}
       for flag in strata}
       for scope in masks}
    for scope in masks:
        for flag in strata:
            for threshold in (20,60,80,100):
                parent=buckets[(scope,flag,"all",f"age_ge{threshold}")]
                children=[buckets[(scope,flag,s,f"age_ge{threshold}")] for s in labels]
                if parent["cells"]!=sum(v["cells"] for v in children):
                    raise ValueError("Older forest species cohort count mismatch")
                for year in YEARS:
                    if not math.isclose(parent["sum_tTS"][year],
                        sum(v["sum_tTS"][year] for v in children),rel_tol=1e-8,abs_tol=.01):
                        raise ValueError("Older forest biomass sum mismatch")
    historic_stability={scope:{group:{label:{
        f"age_ge{min_age}":finish(stable_buckets[(scope,group,label,min_age)])
        for min_age in (20,60,80,100)}
        for label in ("stable_pine","stable_spruce")}
        for group in strata}
        for scope in masks}
    for scope in masks:
        for group in strata:
            for label in ("stable_pine","stable_spruce"):
                for age in (20,60,80,100):
                    cohort=stable_buckets[(scope,group,label,age)]
                    if cohort["cells"]>buckets[(scope,group,"all",f"age_ge{age}")]["cells"]:
                        raise ValueError("Stable cohort exceeds baseline")
                    if age>20 and cohort["cells"]>stable_buckets[(scope,group,label,20)]["cells"]:
                        raise ValueError("Stable cohort increases with age")
    # Row=dominant class in 2005 and column=dominant class in 2010.
    # Reconciliation detects loss and exposes the exact reason a spruce cell
    # does not qualify as stable at each threshold.
    class_names=("pine","spruce","neither","invalid_or_low_volume")
    dominance_audit={}
    for (scope,flag,age,threshold),matrix in dominance_matrices.items():
        cells=int(matrix.sum())
        if cells!=dominance_sensitivity[(scope,flag,age,threshold)]:
            raise ValueError("Dominance matrix total differs from selected cohort")
        parent=buckets[(scope,flag,"all",f"age_ge{age}")]["cells"]
        if cells!=parent:
            raise ValueError("Dominance matrix does not cover whole older cohort")
        entry=dominance_audit.setdefault(scope,{}).setdefault(flag,{}).setdefault(f"age_ge{age}",{})
        spruce_2010=int(matrix[:,1].sum())
        spruce_2005=int(matrix[1,:].sum())
        stable_spruce=int(matrix[1,1])
        entry[threshold]={
            "cells":cells,"classes":list(class_names),"transition_matrix_2005_rows_2010_columns":matrix.tolist(),
            "spruce_dominant_2005_cells":spruce_2005,
            "spruce_dominant_2010_cells":spruce_2010,
            "stable_spruce_cells":stable_spruce,
            "share_stable_of_2010_spruce":stable_spruce/spruce_2010 if spruce_2010 else None,
            "2010_spruce_previously_pine":int(matrix[0,1]),
            "2010_spruce_previously_neither":int(matrix[2,1]),
            "2010_spruce_previously_invalid_or_low":int(matrix[3,1]),
            "2005_spruce_later_pine":int(matrix[1,0]),
            "2005_spruce_later_neither":int(matrix[1,2]),
            "2005_spruce_later_invalid_or_low":int(matrix[1,3])}
    for scope in masks:
        for flag in strata:
            for age in (20,60,80,100):
                ref=dominance_audit[scope][flag][f"age_ge{age}"]["0.6"]
                stable_ref=stable_buckets[(scope,flag,"stable_spruce",age)]["cells"]
                if ref["stable_spruce_cells"]!=stable_ref:
                    raise ValueError("Historical spruce stability does not match audited matrix")
    result={"status":"DESCRIPTIVE_FIXED_CELL_2010_SPECIES_AGE_RECORDED_HARVEST_STRATIFICATION",
      "date_utc":datetime.now(timezone.utc).isoformat(),
      "analysis_crs":"EPSG:3006","cell_size_m":25,
      "original_source_crs":{"2010":"EPSG:3021","2015":"EPSG:3006","2018":"EPSG:3006","nmd":"EPSG:3006","harvest":"EPSG:3006 source REST (4326 output)"},
      "all_full_source_common_cells":total["cells"],
      "harvest_metadata":harvest_meta,
      "masks":{scope:{
       "no_recorded_harvest":finish(buckets[(scope,"no_recorded_harvest","all","all")]),
       "recorded_harvest":finish(buckets[(scope,"recorded_harvest","all","all")])} for scope in masks},
      "strata":summary,"older_age_cohorts":older,"historic_pine_spruce_stability":historic_stability,"historic_dominance_diagnostics":dominance_audit,
      "historical_stability_definition":"Same estimated pine or spruce >=60% of TOTALVOL in both 2005 and 2010. Other species not classified. Requires valid source pixels both years. No observed stand identity inferred.","species_2010_estimate_source":"SLU forest map 2010 PINEVOL, SPRUCEVOL, DECIDUOUSVOL original",
      "species_classification":"pine/spruce/DECIDUOUS>=60pct of their sum, >=20 total volume, <=20pct component-total closure difference; birch not additionally added to DECIDUOUS",
      "biomass_unit":"tonnes dry matter on 25m cell; source-converted from tTS/ha",
      "age_basis":"SLU modelled age in 2010; age groups are not observed chronological cohorts",
      "harvest_strata_not_observed_no_harvest":True,
      "limitations":[
        "No recorded harvest is not evidence that no harvest occurred",
        "Species shares in 2010 are SLU-modelled volume, not observed stand composition",
        "Species/raster source model may be related to 2010 biomass so independence is limited",
        "Volume and biomass source estimates may have systematic nonforest and water positives",
        "No inference that 2015 and SGD2 biomass methods and foliage components are temporally harmonized",
        "Difference in 2015 and 2018 modelled tonnes within cohorts is not a directly measured stock change",
        "Age classes exclude modeled ages >=500; these cells remain in all-age groups",
        "Working geometry may differ from legal administrative municipality boundary",
        "Forest NMD2018 reference applies later-year forest selection and is not 2010 forest map",
      "Stability of modeled 2005/2010 pine/spruce dominance is not verified stable forest cover or absence of thinning",
        "No spatial raster or physical biomass stocks are modified"]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"all_common":total["cells"],
        "mask_totals":result["masks"]},ensure_ascii=False),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--biomass-dir",type=Path,default=Path("release-biomass"))
    p.add_argument("--volume-dir",type=Path,default=Path("release-volume"))
    p.add_argument("--age-dir",type=Path,default=Path("release-age"))
    p.add_argument("--species-dir",type=Path,default=Path("species-2010"))
    p.add_argument("--nmd",type=Path,default=Path("nmd-input/NMD2018bas_BD.tif"))
    p.add_argument("--boundary",type=Path,default=Path("docs/data/lulea_boundary.geojson"))
    p.add_argument("--qa",type=Path,default=Path("metadata/species_biomass_archive_qa.json"))
    p.add_argument("--output",type=Path,default=Path("metadata/biomass_species_age_harvest_2010_2018.json"))
    run(p.parse_args())
