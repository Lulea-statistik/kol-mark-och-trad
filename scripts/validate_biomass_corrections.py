#!/usr/bin/env python3
"""Validate a non-destructive biomass correction overlay against published original-grid samples.

No GeoTIFF is opened or modified. Coordinates are exact EPSG:3006 centers.
A verified replacement value is not a verified carbon mass; that needs physical units.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs/data/biomass_review_snapshot.geojson"
OVERLAY = ROOT / "docs/data/biomass_verified_corrections.json"
OUT = ROOT / "docs/data/biomass_correction_summary.json"

def validate():
    source = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    assert source["metadata"]["input_source_crs"] == "EPSG:3006"
    assert overlay["source_crs"] == "EPSG:3006"
    assert overlay["schema_version"] == 1
    assert overlay["raw_value_units"] == "unverified_source_raw_units", (
        "Changing units requires a separate documented source-unit verification"
    )
    originals = {}
    for feature in source["features"]:
        p = feature["properties"]
        if not p.get("origins") or "user_observation" not in p["origins"]:
            continue
        key = (int(p["east_epsg3006"]), int(p["north_epsg3006"]))
        if key in originals:
            raise ValueError(f"Duplicate original-grid manual center: {key}")
        originals[key] = p

    rows, seen = [], set()
    for correction in overlay["corrections"]:
        key = (correction["east_epsg3006"], correction["north_epsg3006"])
        if not all(type(x) is int for x in key):
            raise ValueError(f"Cell center must be integer EPSG:3006 coordinates: {key}")
        if key in seen or key not in originals:
            raise ValueError(f"Missing/duplicate published original-grid cell: {key}")
        seen.add(key)
        original = originals[key]
        before = original.get("raw_biomass")
        if type(before) not in (int, float) or not math.isfinite(before):
            raise ValueError(f"Original source raw value unavailable: {key}")
        if correction.get("decision") not in ("replace_value", "set_zero", "set_nodata"):
            raise ValueError(f"Invalid correction decision: {key}")
        if correction.get("verified") is not True:
            raise ValueError(f"Only independently verified decisions can enter this layer: {key}")
        if not correction.get("evidence_reference") or not correction.get("verification_date") or not correction.get("verifier"):
            raise ValueError(f"Missing evidence, date or reviewer: {key}")
        if not correction.get("source_epoch_checked") or not correction.get("reference_epoch"):
            raise ValueError(f"Historical source/reference epochs not documented: {key}")
        decision = correction["decision"]
        if decision == "replace_value":
            after = correction.get("replacement_raw_value")
            if type(after) not in (int, float) or not math.isfinite(after) or after < 0:
                raise ValueError(f"Invalid verified replacement raw value: {key}")
        elif decision == "set_zero":
            after = 0
        else:
            after = None  # Explicit NoData; never equate to zero
        if decision == "set_nodata" and correction.get("replacement_raw_value") is not None:
            raise ValueError(f"Do not put a numeric replacement on NoData: {key}")
        delta = after - before if after is not None else None
        rows.append({
            "east_epsg3006": key[0], "north_epsg3006": key[1],
            "reported_context": (original.get("user_observation") or original).get("reported_context"),
            "decision": decision, "original_raw_value": before,
            "verified_new_raw_value": after, "difference_raw": delta,
            "evidence_reference": correction["evidence_reference"],
            "verification_date": correction["verification_date"],
            "source_epoch_checked": correction["source_epoch_checked"],
            "reference_epoch": correction["reference_epoch"],
        })
    numeric = [r["difference_raw"] for r in rows if r["difference_raw"] is not None]
    summary = {
        "schema_version": 1, "source_crs": "EPSG:3006",
        "original_raster_modified": False,
        "source_raw_unit_verified": False,
        "verified_decisions_count": len(rows),
        "numeric_replacements_count": len(numeric),
        "set_nodata_count": len(rows)-len(numeric),
        "sum_numeric_differences_raw": round(math.fsum(numeric), 9),
        "sum_raw_excluded_from_coverage_due_to_nodata": sum(r["original_raw_value"] for r in rows if r["decision"] == "set_nodata"),
        "tonnes_C_delta": None,
        "tonnes_C_delta_status": "Not calculable until source raw units, geographic coverage and cell area are independently verified",
        "note": "A numeric delta excludes any cell changed to NoData; coverage loss is reported separately. This overlay is not a municipality-wide carbon-stock correction.",
        "cell_decisions": rows
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Verified correction layer QA: {len(rows)} decisions; numerical delta {summary['sum_numeric_differences_raw']} source raw units; raster unchanged")

if __name__ == "__main__":
    validate()
