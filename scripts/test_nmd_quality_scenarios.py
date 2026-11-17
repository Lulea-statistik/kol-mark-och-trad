#!/usr/bin/env python3
"""Synthetic self-test only; no claim of real-world QA improvement."""
import unittest
import numpy as np
from scripts.run_nmd2018_lulea_qa import scenario_counter, SCENARIOS, accumulate_scenarios

class QualityScenarioTests(unittest.TestCase):
    def test_overlap_is_removed_once(self):
        v=np.array([[10.,1200.,800.],[0.,1500.,50.]])
        valid=np.array([[True,True,True],[True,False,False]])
        water=np.array([[False,True,True],[True,False,False]])
        total={key:scenario_counter() for key in SCENARIOS}
        accumulate_scenarios(total,valid,v,water)
        self.assertEqual(total["baseline"]["retained_pixels"],4)
        self.assertAlmostEqual(total["baseline"]["retained_raw_sum"],2010.)
        self.assertEqual(total["water_core"]["retained_pixels"],1)
        self.assertAlmostEqual(total["water_core"]["retained_raw_sum"],10.)
        self.assertEqual(total["extreme_gt1000"]["retained_pixels"],3)
        self.assertAlmostEqual(total["extreme_gt1000"]["retained_raw_sum"],810.)
        self.assertEqual(total["water_then_extreme_gt1000"]["retained_pixels"],1)
        self.assertAlmostEqual(total["water_then_extreme_gt1000"]["retained_raw_sum"],10.)
        self.assertEqual(total["baseline"]["remaining_water_core_positive"],2)
        self.assertEqual(total["water_core"]["remaining_water_core_positive"],0)
    def test_empty_mask(self):
        values=np.array([[2.]])
        valid=np.array([[False]])
        water=np.array([[False]])
        total={key:scenario_counter() for key in SCENARIOS}
        accumulate_scenarios(total,valid,values,water)
        self.assertTrue(all(item["retained_pixels"]==0 and item["retained_raw_sum"]==0 for item in total.values()))

if __name__=="__main__":unittest.main()
