#!/usr/bin/env python3
"""Validate map snapshot before public deployment, without touching raster data."""
import csv
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
snapshot=json.loads((ROOT/"docs/data/biomass_review_snapshot.geojson").read_text(encoding="utf-8"))
observations=list(csv.DictReader((ROOT/"docs/data/biomass_user_observations_epsg3006.csv").open(encoding="utf-8",newline="")))
features=snapshot["features"]
assert len(observations)==89, "Expected 89 explicit user-observed locations"
assert len([f for f in features if f["properties"]["origin"]=="harbor_hypothesis"])==2
for obs in observations:
    x,y=float(obs["east_epsg3006"]),float(obs["north_epsg3006"])
    matches=[f for f in features if
             abs(float(f["properties"].get("east_epsg3006",-1))-x)<.01 and
             abs(float(f["properties"].get("north_epsg3006",-1))-y)<.01]
    assert len(matches)==1, (obs,len(matches))
    prop=matches[0]["properties"]
    actual=prop.get("user_observation",prop)
    assert actual["cluster"]==obs["cluster"]
    assert actual["independently_confirmed"] is False
    assert obs["observation_status"]=="user_individually_reviewed"
    assert actual["review_status"]=="user_individually_reviewed"
    assert actual["individually_reviewed"] is True
    assert actual["manual_plausibility_assessment"]==obs["manual_plausibility_assessment"]
    assert "user_observation" in prop["origins"]
assert sum(r["manual_plausibility_assessment"]=="plausible_biomass" for r in observations)==17
assert sum(r["manual_plausibility_assessment"]=="suspected_false_positive" for r in observations)==72
assert snapshot["metadata"]["original_raster_modified"] is False
assert snapshot["metadata"]["independent_errors_confirmed"]==0
print("Review snapshot QA passed: 89 individually reviewed user observations (17 forest-plausible, 72 suspected), zero independent confirmations.")
