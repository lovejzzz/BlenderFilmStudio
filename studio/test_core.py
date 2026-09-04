import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from film_studio import core
class Contracts(unittest.TestCase):
 def setUp(self):self.doc=json.loads((Path(__file__).parent/'projects/last-signal.film.json').read_text())
 def test_both_projects(self):
  for p in (Path(__file__).parent/'projects').glob('*.film.json'):core.validate(json.loads(p.read_text()))
 def test_three_edits_keep_world(self):
  doc=self.doc;original=core.protected_world(doc)
  for note in ['closer','warmer','later cut']:
   proposal=core.quick_proposal(doc,note,'S02');doc=core.apply_patch(doc,proposal)
   self.assertEqual(core.protected_world(doc),original)
  self.assertEqual(doc['revision'],4)
 def test_stale(self):
  p=core.quick_proposal(self.doc,'closer','S01');doc=core.apply_patch(self.doc,p)
  with self.assertRaises(core.StudioError):core.apply_patch(doc,p)
 def test_reject_bad_docs(self):
  attacks=[]
  for key,val in [('script','import os'),('path','../../bad')]:
   d=copy.deepcopy(self.doc);d[key]=val;attacks.append(d)
  for val in [float('nan'),float('inf'),True,-1,2.5]:
   d=copy.deepcopy(self.doc);d['revision']=val;attacks.append(d)
  d=copy.deepcopy(self.doc);d['assets'][0]['params']['python']='pass';attacks.append(d)
  d=copy.deepcopy(self.doc);d['shots'][0]['target']='missing';attacks.append(d)
  d=copy.deepcopy(self.doc);d['assets'][0]['params']['opening']=[0,500,1,1];attacks.append(d)
  for d in attacks:
   with self.assertRaises(core.StudioError):core.validate(d)
 def test_reject_bad_proposals(self):
  base=core.quick_proposal(self.doc,'closer','S01')
  for key,val in [('operation','exec'),('shot','../escape'),('value',float('nan')),('value',-3),('value',True)]:
   p=copy.deepcopy(base);p[key]=val
   with self.assertRaises(core.StudioError):core.apply_patch(self.doc,p)
if __name__=='__main__':unittest.main()
