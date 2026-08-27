#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;SPEC=ROOT/"specs/subpixel-bilinear-tolerance-holdout.v0.1.json";AN=ROOT/"scripts/analyze-b52-d7-bilinear-tolerance.py";sp=importlib.util.spec_from_file_location("d7",AN);mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
class Contract(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.spec=json.loads(SPEC.read_text())
 def test_preregistration(self):self.assertEqual(mod.sha(SPEC),mod.SPEC_SHA256);self.assertEqual(len(self.spec["fixtures"]),6);self.assertEqual(self.spec["formalOutputRoot"],"experiments/subpixel-bilinear-tolerance-holdout-v0-1")
 def test_attacks(self):a=mod.attacks(self.spec);self.assertEqual(len(a),23);self.assertTrue(all(x["passed"] for x in a));self.assertIsNone(mod.first_failure({x:True for x in mod.FIELDS},self.spec))
 def test_two_independent_references_exact(self):
  with tempfile.TemporaryDirectory(prefix="bfs-b52-d7-contract-") as td:
   t=Path(td)
   for f in self.spec["fixtures"]:
    po=t/"py"/f["id"]/"r.rgba32";pr=po.with_suffix(".json");no=t/"node"/f["id"]/"r.rgba32";nr=no.with_suffix(".json")
    p=subprocess.run([self.spec["runtime"]["pythonReference"]["executable"],str(ROOT/"scripts/reference-b52-d7-bilinear.py"),"--spec",str(SPEC),"--fixture",f["id"],"--output",str(po),"--report",str(pr)],cwd=ROOT);n=subprocess.run([self.spec["runtime"]["nodeReference"]["executable"],str(ROOT/"scripts/reference-b52-d7-bilinear.mjs"),"--spec",str(SPEC),"--fixture",f["id"],"--output",str(no),"--report",str(nr)],cwd=ROOT);self.assertEqual(p.returncode,0);self.assertEqual(n.returncode,0);self.assertEqual(po.read_bytes(),no.read_bytes())
 def test_smoke_routes_expected_distribution_failure(self):
  smoke=ROOT/"experiments/subpixel-bilinear-tolerance-preflight-v0-1";pyr=[];nor=[];blr=[];pid=41000
  def run(kind,fid,report,repeat=None):
   nonlocal pid
   pid+=1;r=copy.deepcopy(report);r["pid"]=pid
   if repeat is not None:r["repeat"]=repeat
   r["reportHash"]=mod.ch({k:v for k,v in r.items() if k!="reportHash"})
   return {"kind":kind,"fixtureId":fid,"repeat":repeat,"pid":pid,"exitCode":0,"timedOut":False,"elapsedSeconds":0.0,"reportUri":"development-smoke","report":r}
  for f in self.spec["fixtures"]:
   fid=f["id"]
   pyr.append(run("pythonReference",fid,json.loads((smoke/"reference-smoke/python"/fid/"report.json").read_text())))
   nor.append(run("nodeReference",fid,json.loads((smoke/"reference-smoke/node"/fid/"report.json").read_text())))
   br=json.loads((smoke/"blender-smoke"/fid/"report.json").read_text())
   blr.extend([run("blender",fid,br,1),run("blender",fid,br,2)])
  receipt={"preregistration":{"commit":"bb68af37390ac4459e95ab78f17544446913c01f"},"toolFreezeCommit":"synthetic-contract-only","checks":{"parentIdentity":True,"blenderRuntimeIdentity":True,"pythonRuntimeIdentity":True,"nodeRuntimeIdentity":True,"ocioIdentity":True},"pythonReferenceRuns":pyr,"nodeReferenceRuns":nor,"blenderRuns":blr}
  with tempfile.TemporaryDirectory(prefix="bfs-b52-d7-analysis-") as td:
   result=mod.analyze(self.spec,receipt,Path(td)/"results.json","synthetic-receipt",ROOT)
  self.assertEqual(result["baseFailure"],"TOLERANCE_DISTRIBUTION");self.assertEqual(result["verdict"],self.spec["decision"]["failVerdict"]);self.assertEqual(result["attacksPassed"],23);self.assertTrue(all(v for k,v in result["evidence"].items() if k!="TOLERANCE_DISTRIBUTION"))
if __name__=="__main__":unittest.main()
