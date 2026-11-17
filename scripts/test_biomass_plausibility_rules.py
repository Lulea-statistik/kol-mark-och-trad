import unittest
import numpy as np
from scripts.biomass_plausibility_rules import empty_metrics, update_metrics, review_points

class Rules(unittest.TestCase):
 def test_distinguish_water_core_and_edge_and_high(self):
  values=np.array([[0,1201,10,30],[50,600,0,300]],dtype=float)
  land=np.array([[61,61,61,51],[53,53,52,51]])
  valid=np.ones(values.shape,dtype=bool)
  cores={"water":np.array([[False,True,False,False],[False,False,False,False]]),
         "building":np.array([[False,False,False,True],[False,False,False,True]]),
         "road":np.zeros(values.shape,dtype=bool),
         "developed":np.zeros(values.shape,dtype=bool)}
  result=empty_metrics()
  update_metrics(result,valid,values,land,cores)
  self.assertEqual(result["water_core_positive"]["n"],1)
  self.assertEqual(result["water_edge_positive"]["n"],1)
  self.assertEqual(result["building_core_positive"]["n"],2)
  self.assertEqual(result["high_gt1000"]["n"],1)
  self.assertEqual(result["high_gt500"]["n"],2)
  self.assertEqual(result["high_nonforest_gt500"]["n"],2)
if __name__=="__main__":unittest.main()
