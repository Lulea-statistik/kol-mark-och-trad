#!/usr/bin/env python3
"""Direct-standardization sensitivity to alternate 2010 TOTALVOL bin boundaries.
Uses only 25-unit original-raster aggregate bins. No within-bin interpolation.
"""
import argparse,json,math
from pathlib import Path
import numpy as np

def run(source, min_cells=30):
    fine=source.get("fine_volume_control")
    if not fine:
        raise ValueError("Missing original-raster 25-unit TOTALVOL population; do not approximate from 5 bins")
    edges=fine["volume_2010_edges"]
    assert edges==list(range(0,401,25))+[None],edges
    n=np.asarray(fine["counts"],dtype="int64")
    m={y:np.asarray(fine["mass_tTS"][y],dtype="float64") for y in ("2010","2015","2018")}
    assert n.shape==(6,17,9) and all(x.shape==n.shape for x in m.values())
    assert int(n.sum())==source["age_volume_control"]["population_cells"]
    baseline=source["cohorts"]["age_ge20"]
    assert n.sum(axis=(0,1)).tolist()==baseline["col_2010_cells"]
    for y in m:
        assert np.allclose(m[y].sum(axis=(0,1)),baseline["2010_balance_class_mass_tTS"][y],atol=.02,rtol=1e-9)
    cases={
        "25":list(range(0,401,25))+[math.inf],
        "50":list(range(0,401,50))+[math.inf],
        "100":list(range(0,401,100))+[math.inf],
        "original_50_50_100_100_plus":[0,50,100,200,300,math.inf]
    }
    output={}
    for name,bounds in cases.items():
        counts=[];masses={y:[] for y in m}
        for lo,hi in zip(bounds[:-1],bounds[1:]):
            idx=[j for j in range(17) if edges[j]>=lo and (edges[j]<hi)]
            counts.append(n[:,idx,:].sum(axis=1))
            for y in m:masses[y].append(m[y][:,idx,:].sum(axis=1))
        c=np.stack(counts,axis=1)
        mass={y:np.stack(masses[y],axis=1) for y in m}
        assert np.array_equal(c.sum(axis=1),n.sum(axis=1))
        common=(c>=min_cells).all(axis=2)
        w=c.sum(axis=2)*common
        n_target=int(w.sum())
        if n_target==0:
            output[name]={"status":"INSUFFICIENT_COMMON_SUPPORT","shared_strata":0,
                          "target_population_cells":0,"by_class":None,"volume_edges":bounds[:-1]+[None]}
            continue
        w=w/n_target
        by_class={}
        for j,label in enumerate(source["axis_classes_gran_tall"]):
            cell_count=int(c[:,:,j][common].sum())
            den=np.where(c[:,:,j]>0,c[:,:,j]*.0625,1.)
            est={y:float(np.sum(w*(mass[y][:,:,j]/den))) for y in m}
            by_class[label]={
               "standardized_2018_vs_2010_pct":float(100*(est["2018"]/est["2010"]-1)) if est["2010"]>0 else None,
               "supported_cells":cell_count,
               "coverage_pct":float(100*cell_count/n[:,:,j].sum()),
               "mean_tTS_ha":est}
        output[name]={"status":"VERIFIED_AGGREGATE_STANDARDIZATION",
                      "shared_strata":int(common.sum()),"target_population_cells":n_target,
                      "volume_edges":bounds[:-1]+[None],"by_class":by_class}
    return {"status":"ALTERNATIVE_VOLUME_BINS_SAME_VERIFIED_RASTER","analysis_crs":"EPSG:3006",
            "cell_m":25,"minimum_cells_per_balance_class_per_stratum":min_cells,
            "source_population_cells":int(n.sum()),
            "cases":output,
            "method":"Pooled age x volume weights within case-specific common support; ratio of standardized mean tTS/ha, not mean of ratios; NOT biomass correction."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("docs/data/gran_tall_balans_2005_2010.json"))
    p.add_argument("--output",type=Path,default=Path("docs/data/gran_tall_volymkanslighet_2010_2018.json"))
    args=p.parse_args()
    d=run(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("VOLUME_BIN_SENSITIVITY",[(k,v["status"],v["shared_strata"]) for k,v in d["cases"].items()])
if __name__=="__main__":main()
