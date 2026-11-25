#!/usr/bin/env python3
"""Deterministic tests of failed-source reporting without live downloads."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from probe_growth_raster_metadata import main


def check_unreachable_source():
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        registry=root/"registry.json"
        report=root/"report.json"
        registry.write_text(json.dumps({"sources":[{"id":"source_404",
          "url":"https://example.invalid/absent.tif"}]}),encoding="utf-8")
        with patch.object(sys,"argv",["probe_growth_raster_metadata.py","--registry",str(registry),"--output",str(report)]):
            with patch("rasterio.open",side_effect=OSError("HTTP response code: 404")):
                with patch("urllib.request.urlopen",side_effect=HTTPError("https://example.invalid/absent.tif",404,"Not Found",None,None)):
                    try:
                        main()
                        raise AssertionError("Unverified source incorrectly passed")
                    except SystemExit as error:
                        if "source_404" not in str(error):
                            raise AssertionError(f"Wrong failure diagnostics: {error}")
        item=json.loads(report.read_text(encoding="utf-8"))
        assert item["all_layers_verified"] is False
        assert item["layers"][0]["status"]=="source_read_failed"
        assert "404" in item["layers"][0]["error"]
        assert "404" in item["layers"][0]["http_head_error"]
        print("PASS: unavailable source returns failure and persists actionable diagnostics")


if __name__=="__main__":
    check_unreachable_source()
