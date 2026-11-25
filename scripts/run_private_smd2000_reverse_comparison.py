#!/usr/bin/env python3
"""Run existing PR106 reverse biomass analysis privately, using licensed SMD ZIP.

Run on machine with network, gh CLI authenticated for public source releases,
and Python dependencies from requirements.txt plus fiona. Never sends or writes
SMD to GitHub; private JSON output must reside outside repository checkout.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from zipfile import ZipFile

REPO="Lulea-statistik/kol-mark-och-trad"
SMD_SHA="d85f88e4dcf97a9758c31cbd90ed2681d5d0b5ba62f32d773d59111225fb92f2"
SMD_STEM="data/mdv2580"
NMD_URL="https://geodata.naturvardsverket.se/nedladdning/marktacke/NMD2018/bas_lan_ogen/BD_lan_nmd2018bas_ogeneraliserad_v1_1.zip"
ROOT=Path(__file__).resolve().parents[1]
BIOMASS_TAG="biomass-source-clips-lulea-v1"
VOLUME_TAG="total-wood-volume-lulea-2000-2010-v1"

def hash_file(path):
    h=hashlib.sha256()
    with path.open("rb") as src:
        for b in iter(lambda:src.read(4*1024*1024),b""):h.update(b)
    return h.hexdigest()

def exec_checked(command):
    subprocess.run(command,check=True)

def get_smd(archive,dst):
    if hash_file(archive)!=SMD_SHA:
        raise ValueError("Unrecognized licensed SMD2000 source ZIP: SHA256 mismatch")
    with ZipFile(archive) as zip_file:
        if zip_file.testzip() is not None:raise ValueError("Corrupted SMD2000 ZIP")
        extensions=(".shp",".dbf",".shx",".prj",".cpg")
        files=[]
        for ext in extensions:
            key=SMD_STEM+ext
            if key in zip_file.namelist():files.append((key,dst/("mdv2580"+ext)))
            elif ext in (".shp",".dbf",".shx",".prj"):
                raise ValueError("Missing exact source SMD2000 "+key)
        for name,target in files:
            with zip_file.open(name) as inp,target.open("wb") as out:
                shutil.copyfileobj(inp,out)
    return dst/"mdv2580.shp"

def extract_nmd(zip_path,dst):
    import rasterio
    sys.path.insert(0,str(ROOT/"scripts"))
    from fetch_and_compare_biomass_native import matches_expected_crs
    with ZipFile(zip_path) as z:
        tif_candidates=[f for f in z.infolist()
                if f.filename.lower().endswith(".tif") and "bas" in f.filename.lower()]
        if len(tif_candidates)!=1:raise ValueError("NMD2018 expected one base GeoTIFF")
        tif=tif_candidates[0]
        target=dst/"NMD2018bas_BD.tif"
        with z.open(tif) as inp,target.open("wb") as out:shutil.copyfileobj(inp,out)
        stem=Path(tif.filename).stem.lower()
        tfw=Path(tif.filename).with_suffix(".tfw").name.lower()
        for part in z.infolist():
            if part.is_dir() or part.filename==tif.filename:continue
            name=Path(part.filename).name
            if name.lower().startswith(stem+".") or name.lower()==tfw:
                with z.open(part) as inp,(dst/name).open("wb") as out:shutil.copyfileobj(inp,out)
    with rasterio.open(target) as src:
        if not matches_expected_crs(src.crs,3006) or src.count!=1:
            raise ValueError("Unverified original NMD2018 CRS or band")
        if any(abs(abs(x)-10)>.05 for x in src.res):
            raise ValueError("Invalid NMD2018 source resolution")
    return target

def download_public(dst):
    if not shutil.which("gh"):raise ValueError("GitHub CLI 'gh' is required for public release download")
    bio=dst/"biomass";vol=dst/"volume"
    bio.mkdir();vol.mkdir()
    exec_checked(["gh","release","download",BIOMASS_TAG,"--repo",REPO,
                  "--dir",str(bio),"--pattern","lulea_biomass_*"])
    exec_checked(["gh","release","download",VOLUME_TAG,"--repo",REPO,
                  "--dir",str(vol),"--pattern","lulea_total_volume_2010_*"])
    for y in ("2010","2015","2018"):
        if not (bio/f"lulea_biomass_{y}_source_crs_clip.tif").is_file():
            raise ValueError("Missing biomass archived clip "+y)
    if not (vol/"lulea_total_volume_2010_source_crs_clip.tif").is_file():
        raise ValueError("Missing original source volume 2010")
    # Original release provenance/checksums are validated before data analysis.
    exec_checked([sys.executable,str(ROOT/"scripts/verify_biomass_release.py"),
                  "--directory",str(bio),"--output",str(dst/"biomass_source_integrity.json")])
    nmd_zip=dst/"nmd2018_original.zip"
    with urllib.request.urlopen(NMD_URL,timeout=120) as src,nmd_zip.open("wb") as out:
        shutil.copyfileobj(src,out)
    nmd=extract_nmd(nmd_zip,dst)
    return bio,vol,nmd

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--smd-zip",type=Path,required=True,help="Private original January 2012 SMD2000 ZIP")
    p.add_argument("--output",type=Path,required=True,help="Private report JSON OUTSIDE repo")
    a=p.parse_args()
    archive=a.smd_zip.expanduser().resolve(strict=True)
    output=a.output.expanduser().resolve()
    if output.is_relative_to(ROOT) or output==ROOT:
        raise ValueError("Refuse output inside public Git checkout")
    if output.suffix.lower()!=".json":raise ValueError("Private output filename must end .json")
    if not (ROOT/"scripts/compare_smd2000_reverse_2010_mask_private.py").is_file():
        raise ValueError("Expected PR106 analyzer script missing")
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="smd2000-private-reverse-") as tmp:
        work=Path(tmp)
        source=get_smd(archive,work)
        bio,vol,nmd=download_public(work)
        command=[sys.executable,str(ROOT/"scripts/compare_smd2000_reverse_2010_mask_private.py"),
          "--smd-shp",str(source),"--smd-epsg","3006",
          "--biomass-2010",str(bio/"lulea_biomass_2010_source_crs_clip.tif"),
          "--biomass-2015",str(bio/"lulea_biomass_2015_source_crs_clip.tif"),
          "--biomass-2018",str(bio/"lulea_biomass_2018_source_crs_clip.tif"),
          "--volume-2010",str(vol/"lulea_total_volume_2010_source_crs_clip.tif"),
          "--nmd",str(nmd),"--output",str(output)]
        exec_checked(command)
        data=json.loads(output.read_text(encoding="utf-8"))
        if data.get("status")!="PRIVATE_SMD2000_SENSITIVITY_NOT_VERIFIED_2010_FOREST":
            raise ValueError("Private result not validated")
        for k in ("volume50_all","volume50_smd2000_forest",
                  "volume50_smd2000_forest_or_young","volume50_smd2000_nonwater"):
            x=data["proxy_masks"][k]["all"]
            print(k,{"cells":x["cells"],"hectares":round(x["area_ha"],1),
                     "raw_2010":round(x["sum_raw"]["2010"],2),
                     "raw_2018":round(x["sum_raw"]["2018"],2),
                     "raw_change_percent":x["change_percent_2010_to_2018_raw"]})
    print("Private analysis saved outside repository:",output)
    print("No SMD polygon, GeoTIFF or exact cell geometry sent to GitHub.")
if __name__=="__main__":main()
