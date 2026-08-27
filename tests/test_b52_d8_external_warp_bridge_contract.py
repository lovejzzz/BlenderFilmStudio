#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;SPEC=ROOT/"specs/external-canonical-warp-bridge.v0.1.json";AN=ROOT/"scripts/analyze-b52-d8-external-warp-bridge.py";sp=importlib.util.spec_from_file_location("d8",AN);mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
class Contract(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.spec=json.loads(SPEC.read_text())
 def test_preregistration(self):self.assertEqual(mod.sha(SPEC),mod.SPEC_SHA256);self.assertEqual(self.spec["formalOutputRoot"],"experiments/external-canonical-warp-bridge-v0-1");self.assertEqual(len(self.spec["fixtures"]),3)
 def test_attacks(self):a=mod.attacks(self.spec);self.assertEqual(len(a),24);self.assertTrue(all(x["passed"] for x in a));self.assertIsNone(mod.first_failure({x:True for x in mod.FIELDS},self.spec))
 def test_independent_producers_exact(self):
  with tempfile.TemporaryDirectory(prefix="bfs-b52-d8-contract-") as td:
   t=Path(td)
   for f in self.spec["fixtures"]:
    po=t/"py"/f["id"]/"r.rgba32";pr=po.with_suffix(".json");no=t/"node"/f["id"]/"r.rgba32";nr=no.with_suffix(".json");p=subprocess.run([self.spec["runtime"]["python"]["executable"],str(ROOT/"scripts/reference-b52-d8-external-warp.py"),"--spec",str(SPEC),"--fixture",f["id"],"--output",str(po),"--report",str(pr)],cwd=ROOT,capture_output=True);n=subprocess.run([self.spec["runtime"]["node"]["executable"],str(ROOT/"scripts/reference-b52-d8-external-warp.mjs"),"--spec",str(SPEC),"--fixture",f["id"],"--output",str(no),"--report",str(nr)],cwd=ROOT,capture_output=True);self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(n.returncode,0,n.stderr);self.assertEqual(po.read_bytes(),no.read_bytes())
 def test_development_probe_is_exact_but_nonformal(self):
  o=json.loads((ROOT/"experiments/external-canonical-warp-bridge-development-smoke-v0-1/observation.json").read_text());self.assertEqual(o["classification"],"DEVELOPMENT_ONLY_NOT_FORMAL_EVIDENCE");self.assertTrue(o["blenderOutput"]["exact"]);self.assertEqual(o["blenderOutput"]["changedScalars"],0)
if __name__=="__main__":unittest.main()
