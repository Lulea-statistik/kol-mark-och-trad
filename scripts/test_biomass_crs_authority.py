#!/usr/bin/env python3
"""Regression checks for top-level legacy RT90 WKT authority recognition."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fetch_and_compare_biomass_native import matches_expected_crs as fetch_matches
from compare_biomass_native_area import matches_expected_crs as compare_matches

class WKTStub:
    def __init__(self,wkt): self.wkt=wkt
    def to_wkt(self): return self.wkt
    def to_epsg(self): return None

class LegacyCRSAuthorityTests(unittest.TestCase):
    def test_outer_rt90_authority(self):
        crs=WKTStub('PROJCS["RT90 2.5 gon V",GEOGCS["RT90",AUTHORITY["EPSG","4124"]],AUTHORITY["EPSG","3021"]]')
        for fn in (fetch_matches,compare_matches):
            self.assertTrue(fn(crs,3021))
            self.assertFalse(fn(crs,3006))

    def test_nested_authority_not_accepted(self):
        crs=WKTStub('PROJCS["unknown",GEOGCS["WGS84",AUTHORITY["EPSG","3021"]]]')
        for fn in (fetch_matches,compare_matches):
            self.assertFalse(fn(crs,3021))

    def test_unknown_crs_rejected(self):
        for fn in (fetch_matches,compare_matches):
            self.assertFalse(fn(None,3021))
            self.assertFalse(fn(WKTStub('PROJCS["unknown"]'),3021))

if __name__=="__main__": unittest.main()
