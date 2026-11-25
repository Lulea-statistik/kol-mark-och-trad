#!/usr/bin/env python3
"""Audit the exact archived 2010 biomass TIFF origin and native SLU sidecars.

Source-specific, fail closed. Do NOT guess kg/ha, tonne/ha or components from
magnitude, filenames, historical kNN documentation or adjacent-year products.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
EXPECTED="https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/BIOMASS_XX_P_10.tif"
TEXT_RULES={
 "explicit_kg_ha":r"(?i)(?:kg\s*(?:ts|dm|dry\s*matter)?\s*/\s*ha|kilogram(?:s)?\s*(?:per|/)\s*hectare)",
 "explicit_ton_ha":r"(?i)(?:ton(?:ne|nes)?\s*(?:ts|dm|dry\s*matter)?\s*/\s*ha|ton\s+torrsubstans\s+per\s+hektar)",
 "explicit_roots":r"(?i)(?:r[oö]tter|roots|below[ -]?ground|underjordisk)",
 "explicit_aboveground":r"(?i)(?:above[ -]?ground|ovan[ -]?jordisk|ovanjordisk)",
 "explicit_biomass":r"(?i)biomass|biomassa"
}
def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
    return h.hexdigest()
def text_evidence(path):
    raw=path.read_bytes()
    if len(raw)>1_000_000:raise ValueError("Unexpectedly large metadata sidecar")
    text=raw.decode("utf-8-sig",errors="replace")
    try:
        root=ET.fromstring(raw)
        elems=[]
        for e in root.iter():
            if e.text and e.text.strip():
                name=e.tag.rsplit("}",1)[-1]
                elems.append({"xml_tag":name,"text":e.text.strip()[:500],
                              "attributes":dict(e.attrib)})
        parsed=True
    except ET.ParseError:
        elems=[]
        parsed=False
    hits={}
    for key,pattern in TEXT_RULES.items():
        hits[key]=[]
        for match in list(re.finditer(pattern,text))[:12]:
            snippet=text[max(0,match.start()-130):min(len(text),match.end()+180)]
            hits[key].append(" ".join(snippet.split())[:300])
    return {"name":path.name,"sha256":digest(path),"bytes":len(raw),
            "valid_xml":parsed,"matching_evidence":hits,
            "xml_text_items":elems[:80],"xml_text_items_truncated":len(elems)>80}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--directory",type=Path,default=Path("release-biomass"))
    p.add_argument("--sidecars",type=Path,default=Path("metadata/slu2010_original_sidecars"))
    p.add_argument("--output",type=Path,default=Path("metadata/biomass2010_source_unit_metadata_audit.json"))
    a=p.parse_args()
    prov=a.directory/"lulea_biomass_2010_provenance.json"
    sha=a.directory/"lulea_biomass_2010_SHA256SUMS.txt"
    if not prov.is_file() or not sha.is_file():raise ValueError("Cannot validate archived 2010 provenance")
    d=json.loads(prov.read_text(encoding="utf-8"))
    manifest=json.loads((ROOT/"docs/data/preview/preview_layers.json").read_text(encoding="utf-8"))
    if d.get("origin_url")!=EXPECTED or manifest["layers"]["biomass_2010"]["source"]!=EXPECTED:
        raise ValueError("Archived 2010 TIFF source differs from expected SLU 2010 dataset")
    if d.get("physical_units_verified") is not False:raise ValueError("Unexpected physical-unit assertion")
    if float(d.get("source_scale",-99))!=1 or float(d.get("source_offset",-99))!=0:
        raise ValueError("Source raster native band scale or offset differs from identity")
    if d.get("source_resolution_m")!=[25.0,25.0]:
        raise ValueError("Unexpected native grid resolution")
    if not d.get("source_crs") or '3021' not in d["source_crs"]:
        raise ValueError("Expected source native RT90 EPSG:3021 not established")
    checks={name.strip():hexdigest.strip() for hexdigest,name in (line.split(maxsplit=1) for line in sha.read_text().splitlines() if line.strip())}
    if checks.get(prov.name)!=digest(prov):raise ValueError("Provenance SHA mismatch")
    expected={"BIOMASS_XX_P_10.tif.aux.xml","BIOMASS_XX_P_10.tif.xml"}
    files=sorted(a.sidecars.iterdir()) if a.sidecars.exists() else []
    found={f.name for f in files if f.is_file()}
    if not expected.issubset(found):raise ValueError("Both exact SLU source raster metadata sidecars required")
    evidence=[text_evidence(f) for f in files if f.name in expected]
    unit_hits={k:any(v["matching_evidence"][k] for v in evidence)
             for k in TEXT_RULES}
    # XML text is not an automatically trusted physical unit claim; descriptions
    # can contain both band unit and citation of older datasets. Flag for review.
    status="SOURCE_SIDECARS_AUDITED_PHYSICAL_UNIT_UNVERIFIED"
    result={
      "status":status,
      "audited_utc":datetime.now(timezone.utc).isoformat(),
      "exact_source_url":EXPECTED,
      "source_raster_release_clip_sha256":d["asset_sha256"],
      "source_raster_clip_valid_pixels":d["valid_pixels_inside_project_boundary"],
      "native_crs":"EPSG:3021","native_pixel_m":25,
      "native_scale":d["source_scale"],"native_offset":d["source_offset"],
      "clip_extraction_process":"scripts/cache_biomass_release.py -> scripts/fetch_and_compare_biomass_native.py crop_source: source pixel values read into float32; no numeric kg-ton conversion",
      "metadata_unit_tags":unit_hits,
      "raw_sidecar_evidence":evidence,
      "2010_tonnes_verified":False,
      "2010_biomass_components_verified":False,
      "must_not_publish_2010_physical_mass":True,
      "needs_source_author_confirmation":True,
      "remaining_questions":[
       "Does exact BIOMASS_XX_P_10.tif represent t dry matter/ha or kg dry matter/ha, or another quantity?",
       "Does exact layer contain aboveground only, or also stumps and roots?",
       "Was source imagery, interpolation or component calculation ever adjusted in archived original before clipping?",
       "What are official valid forest/water masks and dates for 2010?",
       "If 2010 differs from 2015/2018, what source-supported, spatially explicit component harmonization is permitted?"
      ]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":status,"source":EXPECTED,"native_scale":d["source_scale"],
       "native_offset":d["source_offset"],"sidecar_signals":unit_hits,
       "sidecar_details":evidence},ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
