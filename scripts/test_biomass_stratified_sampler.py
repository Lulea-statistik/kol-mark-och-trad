import unittest
import numpy as np
from affine import Affine
from scripts.biomass_stratified_sampler import Sampler, classify, STRATA

class SampleDesignTests(unittest.TestCase):
    def test_exclusive_partition_and_probabilities(self):
        val=np.array([[8.,4.,9.,2.],[3.,501.,1.,0.]])
        codes=np.array([[61,62,51,53],[52,111,111,111]])
        valid=np.ones(val.shape,dtype=bool)
        core=np.array([[True,False,False,False],[False,False,False,False]])
        labels=classify(valid,val,codes,core)
        self.assertEqual(labels.tolist(),[[0,1,2,3],[4,5,6,7]])
        sample=Sampler(seed=42,per_stratum=2)
        sample.update(valid,val,codes,core,Affine(10,0,700000,0,-10,7300000))
        self.assertEqual(sum(sample.pop.values()),8)
        self.assertEqual(len(sample.output()),8)
        self.assertTrue(all(r["inclusion_probability"]==1 for r in sample.output()))

    def test_uniform_k_and_reproducibility(self):
        values=np.arange(100,dtype=float).reshape((10,10))+1
        codes=np.full((10,10),111)
        valid=np.ones((10,10),dtype=bool)
        water=np.zeros((10,10),dtype=bool)
        def run():
            sampler=Sampler(seed=100,per_stratum=9)
            sampler.update(valid[:5],values[:5],codes[:5],water[:5],Affine(10,0,0,0,-10,0))
            sampler.update(valid[5:],values[5:],codes[5:],water[5:],Affine(10,0,0,0,-10,-50))
            return sampler
        a,b=run(),run()
        self.assertEqual(a.pop["ordinary_positive"],100)
        self.assertEqual(len(a.output()),9)
        self.assertEqual([r["east_epsg3006"] for r in a.output()],
                         [r["east_epsg3006"] for r in b.output()])
        self.assertTrue(all(abs(r["inclusion_probability"]-.09)<1e-9 for r in a.output()))

    def test_zero_population(self):
        s=Sampler(seed=1)
        s.update(np.zeros((2,2),bool),np.zeros((2,2)),np.zeros((2,2),int),
                 np.zeros((2,2),bool),Affine.identity())
        self.assertEqual(s.output(),[])
        self.assertEqual(sum(s.pop.values()),0)

if __name__=="__main__":unittest.main()
