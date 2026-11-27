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
    # Continuous 2005/2010 pine and spruce shares, conditional on valid
    # TOTALVOL >=20 in both years (not on discrete species classification).
    share_diagnostics=defaultdict(lambda:{
        "cells":0,"sum_2005":0.,"sum_2010":0.,"sum_delta":0.,
        "sum_abs_delta":0.,"sum_delta_squared":0.,
        "delta_bins":[0]*7,"near_60_2005":0,"near_60_2010":0,
        "crossed_60":0,"component_exceeds_total_2005":0,
        "component_exceeds_total_2010":0})
    share_excluded=defaultdict(int)
    share_population=defaultdict(int)
    # Nine joint pine/spruce balance classes: spruce/(spruce+pine).
    # Bins [0,15), [15,25), ... [85,100] percent. End classes
    # include pure pine and pure spruce; zero joint volume is excluded.
    balance_counts={age:np.zeros((9,9),dtype="int64") for age in (20,60,80,100)}
    balance_mass={age:{year:np.zeros(9,dtype="float64") for year in ("2010","2015","2018")}
                  for age in (20,60,80,100)}
    balance_transition_mass={age:{year:np.zeros((9,9),dtype="float64") for year in ("2010","2015","2018")}
                             for age in (20,60,80,100)}
    balance_excluded={age:0 for age in (20,60,80,100)}
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
                # Gran/tall balance is independent of TOTALVOL and deciduous
                # components. Reprojected original species rasters are paired
                # on the exact same EPSG:3006 25m cell grid.
                gt05=pine05+spruce05
                gt10=pine10+spruce10
                balance_valid=(np.isfinite(gt05)&np.isfinite(gt10)&
                               (gt05>0)&(gt10>0))
                share05=np.divide(spruce05,gt05,out=np.zeros_like(gt05),where=gt05>0)
                share10=np.divide(spruce10,gt10,out=np.zeros_like(gt10),where=gt10>0)
                # 0-15% -> 10/90, 15-25% -> 20/80, etc.
                frombin=np.clip(np.floor(share05*10-.5+1e-9).astype("int16"),0,8)
                tobin=np.clip(np.floor(share10*10-.5+1e-9).astype("int16"),0,8)
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
                        if scope=="nmd2018_forest" and group=="no_recorded_harvest":
                            for min_age in (20,60,80,100):
                                candidate=subset&(data["age"]>=min_age)
                                valid=candidate&balance_valid
                                balance_excluded[min_age]+=int(np.count_nonzero(candidate&~balance_valid))
                                if np.any(valid):
                                    pairs=frombin[valid].astype("int64")*9+tobin[valid].astype("int64")
                                    balance_counts[min_age]+=np.bincount(pairs,minlength=81).reshape(9,9)
                                    cols=tobin[valid].astype("int64")
                                    for year in ("2010","2015","2018"):
                                        balance_mass[min_age][year]+=(np.bincount(
                                            cols,weights=data["bio_"+year][valid],minlength=9)*.0625)
                                        balance_transition_mass[min_age][year]+=(np.bincount(
                                            pairs,weights=data["bio_"+year][valid],minlength=81).reshape(9,9)*.0625)

                        for minimum_age in (20,60,80,100):
                            eligible=subset & (data["age"]>=minimum_age)
                            if not eligible.any():continue
                            for threshold,(from_2005,to_2010) in classes_by_threshold.items():
                                key=(scope,group,minimum_age,str(threshold))
                                pair=(from_2005[eligible].astype("int64")*4+
                                      to_2010[eligible].astype("int64"))
                                dominance_matrices[key]+=np.bincount(pair,minlength=16).reshape(4,4)
                                dominance_sensitivity[key]+=int(eligible.sum())
                        # Shares are based on the SAME set of cells in both
                        # years. Report continuous changes in percentage points;
                        # threshold crossing is reported separately. This avoids
                        # treating a marginal crossing as a real species change.
                        valid_share=(
                            np.isfinite(v05)&np.isfinite(v10)&(v05>=20)&(v10>=20)&
                            np.isfinite(pine05)&(pine05>=0)&np.isfinite(spruce05)&(spruce05>=0)&
                            np.isfinite(pine10)&(pine10>=0)&np.isfinite(spruce10)&(spruce10>=0))
                        for min_age in (20,60,80,100):
                            parent_mask=subset & (data["age"]>=min_age)
                            smask=parent_mask & valid_share
                            k=(scope,group,min_age)
                            share_population[k]+=int(parent_mask.sum())
                            share_excluded[k]+=int(np.count_nonzero(parent_mask & ~valid_share))
                            n=int(smask.sum())
                            if n==0:continue
                            for label,source05,source10 in (
                                ("pine",pine05,pine10),("spruce",spruce05,spruce10)):
                                share05=source05[smask]/v05[smask]
                                share10=source10[smask]/v10[smask]
                                delta=(share10-share05)*100.
                                stat=share_diagnostics[(scope,group,min_age,label)]
                                stat["cells"]+=n
                                stat["sum_2005"]+=float(share05.sum(dtype="float64"))
                                stat["sum_2010"]+=float(share10.sum(dtype="float64"))
                                stat["sum_delta"]+=float(delta.sum(dtype="float64"))
                                stat["sum_abs_delta"]+=float(np.abs(delta).sum(dtype="float64"))
                                stat["sum_delta_squared"]+=float(np.square(delta).sum(dtype="float64"))
                                # Bins: <-30, [-30,-15), [-15,-5), [-5,5],
                                # (5,15], (15,30], >30 percentage points.
                                stat["delta_bins"]=[old+int(count) for old,count in zip(
                                    stat["delta_bins"],
                                    np.histogram(delta,bins=[-np.inf,-30,-15,-5,5,15,30,np.inf])[0])]
                                stat["near_60_2005"]+=int(np.count_nonzero(np.abs(share05-.6)<=.05))
                                stat["near_60_2010"]+=int(np.count_nonzero(np.abs(share10-.6)<=.05))
                                stat["crossed_60"]+=int(np.count_nonzero((share05>=.6)!=(share10>=.6)))
                                stat["component_exceeds_total_2005"]+=int(np.count_nonzero(share05>1.000001))
                                stat["component_exceeds_total_2010"]+=int(np.count_nonzero(share10>1.000001))
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
    continuous_shares={}
    labels_delta=["lt_minus_30pp","minus_30_to_minus_15pp",
        "minus_15_to_minus_5pp","minus_5_to_plus_5pp",
        "plus_5_to_plus_15pp","plus_15_to_plus_30pp","gt_plus_30pp"]
    for (scope,group,age,label),stat in share_diagnostics.items():
        n=stat["cells"]
        if n!=sum(stat["delta_bins"]):
            raise ValueError("Continuous share bins do not reconcile")
        expected=buckets[(scope,group,"all",f"age_ge{age}")]["cells"]
        # Continuous shares require TOTALVOL >=20 in *both* years, a
        # stricter condition than the common raster mask (TOTALVOL >=0).
        # Account for excluded low-volume cells explicitly, never set them to 0.
        excluded=share_excluded[(scope,group,age)]
        if n+excluded!=expected or share_population[(scope,group,age)]!=expected:
            raise ValueError(
                f"Continuous share population not matched: {scope}/{group}/{age}, "
                f"valid={n}, excluded_low_volume={excluded}, expected={expected}")
        entry=continuous_shares.setdefault(scope,{}).setdefault(group,{}).setdefault(f"age_ge{age}",{})
        entry[label]={
            "cells":n,
            "eligible_parent_cells":expected,
            "excluded_low_or_invalid_total_volume_cells":excluded,
            "coverage_share":n/expected if expected else None,
            "mean_share_2005_pct":100*stat["sum_2005"]/n,
            "mean_share_2010_pct":100*stat["sum_2010"]/n,
            "mean_delta_percentage_points":stat["sum_delta"]/n,
            "mean_absolute_delta_percentage_points":stat["sum_abs_delta"]/n,
            "rms_delta_percentage_points":math.sqrt(stat["sum_delta_squared"]/n),
            "delta_distribution_cells":dict(zip(labels_delta,stat["delta_bins"])),
            "near_60pct_plus_minus_5pp_2005_cells":stat["near_60_2005"],
            "near_60pct_plus_minus_5pp_2010_cells":stat["near_60_2010"],
            "crossed_60pct_threshold_cells":stat["crossed_60"],
            "component_over_100pct_2005_cells":stat["component_exceeds_total_2005"],
            "component_over_100pct_2010_cells":stat["component_exceeds_total_2010"]}
    for scope in masks:
        for group in strata:
            for age in (20,60,80,100):
                detail=continuous_shares[scope][group][f"age_ge{age}"]
                assert detail["pine"]["cells"]==detail["spruce"]["cells"]
    balance_output={}
    for min_age in (20,60,80,100):
        mat=balance_counts[min_age]
        n=int(mat.sum())
        parent=buckets[("nmd2018_forest","no_recorded_harvest","all",f"age_ge{min_age}")]["cells"]
        if n+balance_excluded[min_age]!=parent:
            raise ValueError("Gran/tall balance coverage does not reconcile")
        cols=mat.sum(axis=0)
        rows=mat.sum(axis=1)
        masses={year:[float(x) for x in balance_mass[min_age][year]]
                for year in ("2010","2015","2018")}
        transitions={year:balance_transition_mass[min_age][year] for year in ("2010","2015","2018")}
        for year in transitions:
            if not np.allclose(transitions[year].sum(axis=0),
                               balance_mass[min_age][year],rtol=1e-9,atol=.01):
                raise ValueError("Gran/tall transition mass does not reconcile with 2010 class mass")
        if any(len(masses[year])!=9 for year in masses):
            raise ValueError("Gran/tall mass dimension")
        balance_output[f"age_ge{min_age}"]={
            "matrix_cells":mat.tolist(),
            "matrix_area_ha":(mat.astype(float)*.0625).tolist(),
            "matrix_biomass_tTS":{year:transitions[year].tolist() for year in transitions},
            "matrix_biomass_difference_2018_vs_2010_pct":[
                [float(100*(transitions["2018"][i,j]/transitions["2010"][i,j]-1))
                  if transitions["2010"][i,j]>0 else None for j in range(9)]
                for i in range(9)],
            "cells":n,"area_ha":n*.0625,
            "excluded_zero_pine_plus_spruce":balance_excluded[min_age],
            "row_2005_cells":rows.tolist(),"col_2010_cells":cols.tolist(),
            "2010_balance_class_mass_tTS":masses,
            "2010_balance_class_density_tTS_ha":{
                year:[float(masses[year][i]/(cols[i]*.0625)) if cols[i] else None for i in range(9)]
                for year in masses},
            "density_change_2018_vs_2010_pct":[
                float(100*(masses["2018"][i]/masses["2010"][i]-1))
                if masses["2010"][i]>0 else None for i in range(9)]}
        for year in ("2010","2015","2018"):
            if not math.isclose(float(transitions[year].sum()),sum(masses[year]),
                                rel_tol=1e-9,abs_tol=.01):
                raise ValueError("Gran/tall biomass mass closure invalid")
        if n!=sum(rows) or n!=sum(cols):
            raise ValueError("Gran/tall balance marginals do not reconcile")
    result={"status":"DESCRIPTIVE_FIXED_CELL_2010_SPECIES_AGE_RECORDED_HARVEST_STRATIFICATION",
      "date_utc":datetime.now(timezone.utc).isoformat(),
      "analysis_crs":"EPSG:3006","cell_size_m":25,
      "original_source_crs":{"2010":"EPSG:3021","2015":"EPSG:3006","2018":"EPSG:3006","nmd":"EPSG:3006","harvest":"EPSG:3006 source REST (4326 output)"},
      "all_full_source_common_cells":total["cells"],
      "harvest_metadata":harvest_meta,
      "masks":{scope:{
       "no_recorded_harvest":finish(buckets[(scope,"no_recorded_harvest","all","all")]),
       "recorded_harvest":finish(buckets[(scope,"recorded_harvest","all","all")])} for scope in masks},
      "strata":summary,"older_age_cohorts":older,"historic_pine_spruce_stability":historic_stability,"historic_dominance_diagnostics":dominance_audit,"continuous_species_shares":continuous_shares,"gran_tall_balance":balance_output,
      "gran_tall_balance_method":"2005 and 2010 SPRUCEVOL/(SPRUCEVOL+PINEVOL) 9 bins 10/90 through 90/10; zero joint conifer volume excluded, forest NMD2018 and no recorded 2011-2018 harvest. Biomass per 2010 balance class.",
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
        "Pine and spruce shares are fractions of modeled TOTALVOL; sums may be less or greater than 100 pct because other species and model inconsistencies exist",
        "No spatial raster or physical biomass stocks are modified"]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Publish a compact JSON subset for the website, without duplicating
    # the large diagnostic raster result.
    if args.balance_web_output:
        payload={"status":"VERIFIED_ORIGINAL_RASTER_COMPARISON",
            "source_crs":{"2005":"EPSG:3021","2010":"EPSG:3021","2015":"EPSG:3006","2018":"EPSG:3006"},
            "analysis_crs":"EPSG:3006","cell_m":25,"area_per_cell_ha":.0625,
            "axis_classes_gran_tall":["10/90","20/80","30/70","40/60","50/50","60/40","70/30","80/20","90/10"],
            "source_computation":"SPRUCEVOL/(SPRUCEVOL+PINEVOL) per historical year",
            "forest_mask":"NMD2018 forest, no recorded harvest 2011-2018",
            "cohorts":balance_output}
        args.balance_web_output.parent.mkdir(parents=True,exist_ok=True)
        args.balance_web_output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    print(json.dumps({"status":result["status"],"all_common":total["cells"],
        "mask_totals":result["masks"]},ensure_ascii=False),flush=True)

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
    p.add_argument("--balance-web-output",type=Path,default=Path("docs/data/gran_tall_balans_2005_2010.json"))
    run(p.parse_args())
