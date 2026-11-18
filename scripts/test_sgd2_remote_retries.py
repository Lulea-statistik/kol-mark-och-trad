"""Synthetic tests: SLU connection failures must retry and then fail closed."""
import unittest
from unittest.mock import patch
from rasterio.errors import RasterioIOError
from scripts.run_nmd2018_lulea_qa import open_remote_biomass

class RemoteSourceRetries(unittest.TestCase):
    @patch("scripts.run_nmd2018_lulea_qa.time.sleep")
    @patch("scripts.run_nmd2018_lulea_qa.rasterio.open")
    def test_transient_recovery(self, opener, sleeper):
        expected=object()
        opener.side_effect=[RasterioIOError("connection refused"),expected]
        got=open_remote_biomass("https://gis.slu.se/example.tif",attempts=3,delay_seconds=1)
        self.assertIs(got,expected)
        self.assertEqual(opener.call_count,2)
        sleeper.assert_called_once_with(1)

    @patch("scripts.run_nmd2018_lulea_qa.time.sleep")
    @patch("scripts.run_nmd2018_lulea_qa.rasterio.open")
    def test_persistent_outage_raises_not_fallback(self, opener, sleeper):
        opener.side_effect=RasterioIOError("connection refused")
        with self.assertRaises(RasterioIOError):
            open_remote_biomass("https://gis.slu.se/example.tif",attempts=3,delay_seconds=1)
        self.assertEqual(opener.call_count,3)
        self.assertEqual(sleeper.call_count,2)

if __name__=="__main__":
    unittest.main()
