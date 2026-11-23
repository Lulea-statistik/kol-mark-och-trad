#!/usr/bin/env python3
"""Regression test for unsigned native biomass pixel arrays and masked NoData."""
import unittest
import numpy as np

class MaskedRasterNoDataTests(unittest.TestCase):
    def test_uint16_mask_is_preserved_on_float_conversion(self):
        source=np.ma.array(
            np.array([[0,42],[65535,300]],dtype=np.uint16),
            mask=[[False,False],[True,False]]
        )
        converted=np.ma.asarray(source,dtype="float32").filled(-9999.0)
        self.assertEqual(converted.dtype,np.dtype("float32"))
        np.testing.assert_array_equal(
            converted,np.array([[0,42],[-9999,300]],dtype="float32")
        )
        self.assertEqual(converted[0,0],0)  # valid zeros must not become NoData

if __name__=="__main__":
    unittest.main()
