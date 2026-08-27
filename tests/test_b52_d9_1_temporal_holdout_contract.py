#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, subprocess, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
SPEC=ROOT/"specs/layer-depth-temporal-accumulation-holdout.v0.1.json"
ANALYZER=ROOT/"scripts/analyze-b52-d9-1-temporal-holdout.py"
loader=importlib.util.spec_from_file_location("d9_1_analyzer",ANALYZER); analyzer=importlib.util.module_from_spec(loader); loader.loader.exec_module(analyzer)
class Contract(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.spec=json.loads(SPEC.read_text())
 def test_preregistration_identity_and_freshness(self):
  self.assertEqual(analyzer.sha(SPEC),analyzer.SPEC_SHA256); self.assertEqual(self.spec["experimentId"],"B52-D9.1"); self.assertEqual(len(self.spec["fixtures"]),4); self.assertEqual(len({tuple(x["resolution"]) for x in self.spec["fixtures"]}),4); self.assertFalse((ROOT/"experiments/layer-depth-temporal-accumulation-calibration-v0-1").exists()); self.assertFalse(self.spec["freshness"]["reuseD9ConstantColorSurfaces"])
 def test_attack_contract(self):
  attacks=analyzer.synthetic_attacks(self.spec); self.assertEqual(len(attacks),30); self.assertTrue(all(x["passed"] for x in attacks)); self.assertIsNone(analyzer.first_failure({x:True for x in self.spec["attacks"]},self.spec))
 def test_dual_producers_all_arrays_exact(self):
  with tempfile.TemporaryDirectory(prefix="bfs-b52-d9-1-contract-") as td:
   temp=Path(td)
   for fixture in self.spec["fixtures"]:
    dirs={}
    for producer,exe,tool in (("python",self.spec["runtime"]["python"]["executable"],ROOT/"scripts/reference-b52-d9-1-temporal.py"),("node",self.spec["runtime"]["node"]["executable"],ROOT/"scripts/reference-b52-d9-1-temporal.mjs")):
     out=temp/producer/fixture["id"]/"arrays"; report=temp/producer/fixture["id"]/"report.json"; run=subprocess.run([exe,str(tool),"--spec",str(SPEC),"--fixture",fixture["id"],"--output-dir",str(out),"--report",str(report)],cwd=ROOT,capture_output=True); self.assertEqual(run.returncode,0,run.stderr); dirs[producer]=out
    for filename in analyzer.FILES.values(): self.assertEqual((dirs["python"]/filename).read_bytes(),(dirs["node"]/filename).read_bytes(),f"{fixture['id']} {filename}")
 def test_independent_truth_and_frozen_sensitivity(self):
  naive=set(self.spec["sensitivityControls"]["naiveUnconditionalHistory"]["applicableFixtures"]); wrong=set(self.spec["sensitivityControls"]["wrongMotionSign"]["applicableFixtures"])
  for fixture in self.spec["fixtures"]:
   truth=analyzer.truth(self.spec,fixture); self.assertTrue((truth["resolvedRgba"]==truth["cleanTarget"]).all()); nm=analyzer.metric(analyzer.accumulate(truth,naive=True),truth["cleanTarget"]); wm=analyzer.metric(analyzer.accumulate(truth,sign=-1),truth["cleanTarget"])
   if fixture["id"] in naive: self.assertGreaterEqual(nm["wrongPixels"],32); self.assertGreaterEqual(nm["maximumAbsoluteError"],.25)
   if fixture["id"] in wrong: self.assertGreaterEqual(wm["wrongPixels"],32); self.assertGreaterEqual(wm["maximumAbsoluteError"],.25)
   if fixture["id"]=="TEXTURED_STATIC_CONTROL_71X43": self.assertTrue(truth["analyticValidity"].all()); self.assertEqual(wm["wrongPixels"],0)
 def test_d9_counterexample_is_retained(self):
  observation=ROOT/self.spec["parents"]["d9DevelopmentObservation"]["uri"]; result=ROOT/self.spec["parents"]["d9InvalidResult"]["uri"]; self.assertEqual(analyzer.sha(observation),self.spec["parents"]["d9DevelopmentObservation"]["sha256"]); self.assertEqual(analyzer.sha(result),self.spec["parents"]["d9InvalidResult"]["sha256"]); self.assertIn("DESIGN_INVALID",observation.read_text())
if __name__=="__main__": unittest.main()
