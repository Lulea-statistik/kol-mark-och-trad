"""Rule-based *candidates* for independent biomass plausibility review.

This module NEVER treats a high number or categorical coincidence as proof
of error. In particular, 500/1000 are sensitivity thresholds, not deletion
thresholds. Criteria are source- and grid-aware, and all outcomes are flags.
"""
import numpy as np

LABELS = {
    "water_core_positive": "High priority: biomass >0 in 3x3 stable NMD water",
    "water_edge_positive": "Review: biomass >0 at NMD water edge",
    "building_core_positive": "Review: biomass >0 in 3x3 NMD building class",
    "road_core_positive": "Review: biomass >0 in 3x3 NMD road class",
    "developed_core_positive": "Review: biomass >0 in other developed land",
    "high_gt500": "Value review: raw biomass >500 (unvalidated threshold)",
    "high_gt1000": "Value review: raw biomass >1000 (unvalidated threshold)",
    "high_nonforest_gt500": "Priority review: raw >500 and NMD water/built/road",
}
def empty_metrics():
    return {key: {"n":0, "raw_sum":0.0} for key in LABELS}
def add(metrics, key, mask, values):
    count = int(np.count_nonzero(mask))
    metrics[key]["n"] += count
    metrics[key]["raw_sum"] += float(np.sum(values[mask], dtype="float64"))

def update_metrics(metrics, valid, values, classes, core_masks):
    """Class codes are NMD2018 basskikt, native SGD2 grid, shared valid pixels."""
    positive = valid & (values > 0)
    water = np.isin(classes, (61,62))
    built = classes == 51
    road = classes == 53
    developed = classes == 52
    water_core = core_masks["water"]
    add(metrics,"water_core_positive",positive & water_core,values)
    add(metrics,"water_edge_positive",positive & water & ~water_core,values)
    add(metrics,"building_core_positive",positive & built & core_masks["building"],values)
    add(metrics,"road_core_positive",positive & road & core_masks["road"],values)
    add(metrics,"developed_core_positive",positive & developed & core_masks["developed"],values)
    add(metrics,"high_gt500",valid & (values > 500),values)
    add(metrics,"high_gt1000",valid & (values > 1000),values)
    add(metrics,"high_nonforest_gt500",valid & (values > 500) & (water | built | road),values)

def review_points(valid, values, classes, core_masks, transform, max_points=300):
    """Deterministically keep highest raw values per class/flag as review candidates.

    Sampling is purposefully non-random; it is a TRIAGE queue, not an unbiased
    accuracy estimate. Produce EPSG:3006 cell centers; do not infer EPSG.
    """
    out=[]
    priority = {
        "water": valid & (values>0) & core_masks["water"],
        "building": valid & (values>0) & core_masks["building"] & (classes==51),
        "road": valid & (values>0) & core_masks["road"] & (classes==53),
        "high": valid & (values>500),
    }
    per=max(1,max_points//4)
    for label,mask in priority.items():
        coords=np.argwhere(mask)
        if not len(coords):continue
        rank=np.argsort(values[mask],kind="stable")[::-1][:per]
        for row,col in coords[rank]:
            x,y=transform*(float(col)+0.5,float(row)+0.5)
            out.append({"rule":label,"east":round(x,2),"north":round(y,2),
                        "nmd_code":int(classes[row,col]),"raw_value":float(values[row,col]),
                        "status":"needs_independent_validation"})
    return out
