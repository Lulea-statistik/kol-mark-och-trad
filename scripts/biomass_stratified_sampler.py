"""Reproducible, per-cell uniform random samples from mutually exclusive strata.

Reservoir: retain the n smallest U(0,1) keys across every eligible pixel.
Conditional on a fixed stratum, this is simple random sampling WITHOUT
replacement. No independent ground truth or raster modification is implied.
"""
import heapq
import numpy as np

STRATA=("water_core_positive","water_edge_positive","building_positive",
        "road_positive","developed_positive","high_other_positive",
        "ordinary_positive","zero_control")
SEED=20181117
PER_STRATUM=30

def classify(valid, vals, nmd, water_core):
    """Assign each original joint-valid pixel to exactly one stratum."""
    result=np.full(valid.shape,-1,dtype=np.int8)
    pos=valid & (vals>0)
    # Priority is explicit; the first matching rule wins.
    tests=(
       pos & water_core,
       pos & np.isin(nmd,(61,62)),
       pos & (nmd==51),
       pos & (nmd==53),
       pos & (nmd==52),
       pos & (vals>500),
       pos,
       valid & (vals==0),
    )
    for idx,test in enumerate(tests):
        result[(result<0)&test]=idx
    if np.any(valid & (result<0)):
        raise ValueError("Joint-valid pixel left unclassified")
    return result

class Sampler:
    def __init__(self,seed=SEED,per_stratum=PER_STRATUM):
        self.rng=np.random.default_rng(seed)
        self.k=per_stratum
        self.pop={s:0 for s in STRATA}
        self.heaps={s:[] for s in STRATA}
        self.seed=seed

    def update(self,valid,vals,nmd,water_core,affine):
        classes=classify(valid,vals,nmd,water_core)
        # Draw keys also on invalid pixels to keep per-tile logic simple.
        keys=self.rng.random(size=vals.shape)
        for ix,name in enumerate(STRATA):
            hit=classes==ix
            n=int(np.count_nonzero(hit))
            self.pop[name]+=n
            if not n:continue
            flat=np.flatnonzero(hit)
            # Only inspect k smallest tile keys; a tile cannot contribute
            # more than k samples to the global k-minimum reservoir.
            order=np.argpartition(keys.ravel()[flat],min(self.k,n)-1)[:min(self.k,n)]
            for v in flat[order]:
                y,x=np.unravel_index(v,vals.shape)
                east,north=affine*(float(x)+0.5,float(y)+0.5)
                rank=float(keys[y,x])
                record={"stratum":name,"east_epsg3006":round(east,2),
                        "north_epsg3006":round(north,2),
                        "nmd_code":int(nmd[y,x]),"raw_biomass":float(vals[y,x]),
                        "random_key":rank}
                heap=self.heaps[name]
                node=(-rank,record["east_epsg3006"],record["north_epsg3006"],record)
                if len(heap)<self.k:heapq.heappush(heap,node)
                elif node[0]>heap[0][0]:heapq.heapreplace(heap,node)

    def output(self):
        rows=[]
        for s in STRATA:
            for node in sorted(self.heaps[s],reverse=True):
                r=node[-1].copy()
                r["population_n"]=self.pop[s]
                r["sample_n"]=min(self.pop[s],self.k)
                r["inclusion_probability"]=r["sample_n"]/r["population_n"]
                r["sampling_method"]="stratified_simple_random_without_replacement"
                r["review_status"]="not_reviewed"
                rows.append(r)
        return rows
