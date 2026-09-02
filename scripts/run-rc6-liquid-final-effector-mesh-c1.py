#!/usr/bin/env python3
"""Persist verified Data state, reopen it, and run one Mesh-only reconstruction."""

import hashlib, json, os, shutil, subprocess, time
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
RETAINED_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-data-attempt-42")
RETAINED_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-final-effector-data-attempt-42"
RETAINED_CACHE = RETAINED_WORK / "final-effector-plus1/mantaflow-cache"
FAILURE_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-attempt-44"
FAILURE_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-attempt-44")
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c1-attempt-45")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-c1-attempt-45"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
ADOPT_TOOL = RESEARCH / "scripts/run-rc6-liquid-final-effector-mesh-c1-adopt-scene.py"
MESH_TOOL = RESEARCH / "scripts/run-rc6-liquid-final-effector-mesh-c1-scene.py"
RUNNER = Path(__file__).resolve(); AUDITOR = RESEARCH / "scripts/audit-rc6-liquid-final-effector-mesh-c1.py"; SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-final-effector-mesh-c1-tool-freeze.v0.50.json"
CELL_ID = "final-effector-mesh-c1"; BANNED_MEDIA = {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"}

def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"))
def self_hash(v, f): b=dict(v); b.pop(f,None); return hashlib.sha256(canonical(b).encode()).hexdigest()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read_json(p): return json.loads(p.read_text())
def write_exclusive(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x") as h: json.dump(v,h,indent=2,sort_keys=True); h.write("\n")
def manifest(root, exclusions=()):
    ex=set(exclusions); files=[{"path":str(p.relative_to(root)),"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink() and str(p.relative_to(root)) not in ex]; v={"schemaVersion":"bfs.rootManifest.v0.1","root":str(root),"files":files}; v["manifestHash"]=self_hash(v,"manifestHash"); return v
def expected_data(): return sorted([f"config/config_{f:04d}.uni" for f in range(1,8)]+[f"data/fluid_data_{f:04d}.vdb" for f in range(1,8)])
def expected_all(): return sorted(expected_data()+[f"mesh/fluid_mesh_{f:04d}.bobj.gz" for f in range(1,8)])
def roster(root): return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
def data_manifest(root):
    files=[]
    for r in expected_data():
        p=root/r
        if not p.is_file() or p.is_symlink(): raise RuntimeError(f"C1 Data missing: {r}")
        files.append({"path":r,"bytes":p.stat().st_size,"sha256":sha(p)})
    v={"schemaVersion":"bfs.rc6LiquidDataManifest.v0.1","files":files}; v["manifestHash"]=self_hash(v,"manifestHash"); return v
def tree_bytes(root): return sum(p.stat().st_size for p in root.rglob("*") if p.is_file() and not p.is_symlink())
def argv(tool, blend): return [str(BINARY),"--background","--factory-startup","--disable-autoexec","--offline-mode",str(blend),"--python",str(tool),"--","--cell-id",CELL_ID,"--work-root",str(WORK),"--evidence-root",str(EVIDENCE),"--retained-data-manifest-hash",RETAINED_DATA_HASH] + ([] if tool==ADOPT_TOOL else ["--mesh-particle-radius","9.0"])
def signed_pass(result,t):
    for s in result["samples"]:
        pos=[x for x in s["components"] if x["signedVolumeCubicMeters"]>1e-12]; neg=[x for x in s["components"] if x["signedVolumeCubicMeters"]<-1e-12]
        if len(pos)!=t["requiredPositiveWaterBodiesPerFrame"] or len(neg)>t["maximumNegativeNestedShellCount"] or any(x["nonManifoldEdgeCount"] for x in s["components"]): return False
        for inner in neg:
            outer=pos[0]
            if any(inner["boundsMinWorld"][a]<outer["boundsMinWorld"][a]-1e-7 or inner["boundsMaxWorld"][a]>outer["boundsMaxWorld"][a]+1e-7 for a in range(3)): return False
            if sum((inner["centroidWorld"][a]-outer["centroidWorld"][a])**2 for a in range(3))**0.5>t["maximumNestedCentroidSeparationMeters"]: return False
    return True
def scientific_pass(result,t):
    m=result["metrics"]; return m["maximumAbsoluteSourceVolumeErrorFraction"]<=t["maximumAbsoluteSourceVolumeErrorFraction"] and m["maximumAbsoluteVolumeDriftFraction"]<=t["maximumAbsoluteTemporalDriftFraction"] and m["maximumOutsideCupInteriorPlusOneVoxelFraction"]<=t["maximumOutsideCupInteriorPlusOneVoxelFraction"] and m["maximumNonManifoldEdgeCount"]==0 and signed_pass(result,t)

RETAINED_DATA_HASH=data_manifest(RETAINED_CACHE)["manifestHash"] if RETAINED_CACHE.is_dir() else ""

def main():
    if WORK.exists() or EVIDENCE.exists(): raise RuntimeError("C1 roots are not fresh")
    if subprocess.run(["git","status","--porcelain"],cwd=RESEARCH,capture_output=True,text=True,check=True).stdout: raise RuntimeError("research worktree must be clean")
    spec=read_json(SPEC)
    if spec.get("status")!="FROZEN" or spec.get("specHash")!=self_hash(spec,"specHash"): raise RuntimeError("C1 spec mismatch")
    tools={str(ADOPT_TOOL.relative_to(RESEARCH)):sha(ADOPT_TOOL),str(MESH_TOOL.relative_to(RESEARCH)):sha(MESH_TOOL),str(RUNNER.relative_to(RESEARCH)):sha(RUNNER),str(AUDITOR.relative_to(RESEARCH)):sha(AUDITOR)}
    if spec.get("tools")!=tools: raise RuntimeError("C1 tools mismatch")
    if sha(BINARY)!=spec["inputs"]["binarySha256"] or sha(SOURCE_BLEND)!=spec["inputs"]["sourceBlendSha256"]: raise RuntimeError("C1 inputs mismatch")
    retained_work=read_json(RETAINED_EVIDENCE/"work-manifest.json"); retained_receipt=read_json(RETAINED_EVIDENCE/"receipt.json"); retained_audit=read_json(RETAINED_EVIDENCE/"independent-audit.json"); retained_data=data_manifest(RETAINED_CACHE)
    if manifest(RETAINED_WORK)!=retained_work or retained_work["manifestHash"]!=spec["inputs"]["retainedWorkManifestHash"] or retained_receipt["receiptHash"]!=spec["inputs"]["retainedReceiptHash"] or retained_audit["auditHash"]!=spec["inputs"]["retainedAuditHash"] or retained_data["manifestHash"]!=spec["inputs"]["retainedDataManifestHash"]: raise RuntimeError("C1 retained accepted inputs drift")
    if manifest(FAILURE_EVIDENCE)["manifestHash"]!=spec["retainedFailure"]["evidenceRootManifestHash"] or manifest(FAILURE_WORK)["manifestHash"]!=spec["retainedFailure"]["workRootManifestHash"] or read_json(FAILURE_EVIDENCE/"processes/01-final-effector-mesh.json")["processHash"]!=spec["retainedFailure"]["processHash"]: raise RuntimeError("C1 retained failure drift")
    c=spec["resourceCeilings"]; free_before=shutil.disk_usage(WORK.parent).free
    if free_before<c["minimumFreeBytesBefore"] or free_before<c["minimumFreeBytesAfter"]+c["projectedWriteBytes"]: raise RuntimeError("C1 resource admission")
    for root in (WORK,EVIDENCE): root.mkdir(parents=True,exist_ok=False)
    for root in (WORK/"user/config",WORK/"user/scripts",WORK/"user/datafiles",WORK/"user/extensions",EVIDENCE/"logs",EVIDENCE/"processes",EVIDENCE/"cells"): root.mkdir(parents=True,exist_ok=False)
    cell=WORK/CELL_ID; cell.mkdir(parents=True,exist_ok=False); shutil.copy2(SOURCE_BLEND,cell/"source-state.blend"); shutil.copytree(RETAINED_CACHE,cell/"mantaflow-cache",symlinks=False)
    if data_manifest(cell/"mantaflow-cache")!=retained_data: raise RuntimeError("C1 copied Data drift")
    write_exclusive(EVIDENCE/"retained-data-manifest.json",retained_data)
    admission={"schemaVersion":"bfs.rc6LiquidFinalEffectorMeshC1Admission.v0.1","status":"PASS","researchCommit":subprocess.run(["git","rev-parse","HEAD"],cwd=RESEARCH,capture_output=True,text=True,check=True).stdout.strip(),"freeBytesBefore":free_before,"binarySha256":sha(BINARY),"sourceBlendSha256":sha(SOURCE_BLEND),"retainedDataManifestHash":RETAINED_DATA_HASH,"retainedFailureProcessHash":spec["retainedFailure"]["processHash"],"specHash":spec["specHash"]}; admission["admissionHash"]=self_hash(admission,"admissionHash"); write_exclusive(EVIDENCE/"admission.json",admission)
    env=dict(os.environ); env.update({"BLENDER_USER_CONFIG":str(WORK/"user/config"),"BLENDER_USER_SCRIPTS":str(WORK/"user/scripts"),"BLENDER_USER_DATAFILES":str(WORK/"user/datafiles"),"BLENDER_USER_EXTENSIONS":str(WORK/"user/extensions")})
    processes=[]
    for index,(tool,blend,marker) in enumerate([(ADOPT_TOOL,cell/"source-state.blend","RC6_FINAL_EFFECTOR_DATA_ADOPT="),(MESH_TOOL,cell/"data-adopted-state.blend","RC6_FINAL_EFFECTOR_MESH_C1=")],1):
        out=EVIDENCE/"logs"/f"{index:02d}.stdout.log"; err=EVIDENCE/"logs"/f"{index:02d}.stderr.log"; av=argv(tool,blend); started=time.monotonic()
        with out.open("xb") as oh,err.open("xb") as eh: done=subprocess.run(av,cwd=RESEARCH,env=env,stdout=oh,stderr=eh,check=False)
        proc={"schemaVersion":"bfs.rc6LiquidFinalEffectorMeshC1Process.v0.1","index":index,"argv":av,"cwd":str(RESEARCH),"exitCode":done.returncode,"wallSeconds":round(time.monotonic()-started,6),"stdoutSha256":sha(out),"stderrSha256":sha(err)}; proc["processHash"]=self_hash(proc,"processHash"); write_exclusive(EVIDENCE/"processes"/f"{index:02d}.json",proc); processes.append(proc)
        if done.returncode!=0 or err.stat().st_size!=0 or marker not in out.read_text(errors="replace"): raise RuntimeError(f"C1 Blender process {index} failed")
        if data_manifest(cell/"mantaflow-cache")!=retained_data: raise RuntimeError(f"C1 process {index} changed Data")
    adoption=read_json(EVIDENCE/"cells/adoption/result.json"); result=read_json(EVIDENCE/f"cells/{CELL_ID}/result.json")
    if adoption.get("status")!="ADOPTED" or adoption.get("resultHash")!=self_hash(adoption,"resultHash") or result.get("schemaVersion")!="bfs.rc6LiquidFinalEffectorMeshC1Cell.v0.1" or result.get("resultHash")!=self_hash(result,"resultHash") or roster(cell/"mantaflow-cache")!=expected_all(): raise RuntimeError("C1 result identity or roster mismatch")
    t=spec["acceptanceThresholds"]; status="PASS_FINAL_EFFECTOR_MESH_C1_STATIC" if scientific_pass(result,t) else "FAIL_FINAL_EFFECTOR_MESH_C1_STATIC"; work_bytes=tree_bytes(WORK); evidence_bytes=tree_bytes(EVIDENCE); free_after=shutil.disk_usage(WORK.parent).free
    if work_bytes>c["workBytes"] or evidence_bytes>c["evidenceBytes"] or free_after<c["minimumFreeBytesAfter"]: status="FAIL_RESOURCE_CEILING"
    if any(p.is_symlink() for root in (WORK,EVIDENCE) for p in root.rglob("*")): status="FAIL_SYMLINK"
    if any(p.is_file() and p.suffix.lower() in BANNED_MEDIA for root in (WORK,EVIDENCE) for p in root.rglob("*")): status="FAIL_RENDER_MEDIA"
    receipt={"schemaVersion":"bfs.rc6LiquidFinalEffectorMeshC1Receipt.v0.1","status":status,"slowTipUnlocked":status=="PASS_FINAL_EFFECTOR_MESH_C1_STATIC","adoptionResultHash":adoption["resultHash"],"meshResultHash":result["resultHash"],"metrics":result["metrics"],"signedTopologyPass":signed_pass(result,t),"counts":{"blenderStarts":2,"cacheStateAdoptions":1,"fluidDataBakes":0,"fluidMeshBakes":1,"blendSaves":2,"renderCalls":0,"networkCalls":0,"engineRemoteWrites":0},"processHashes":[p["processHash"] for p in processes],"retainedDataManifestHash":RETAINED_DATA_HASH,"resources":{"freeBytesBefore":free_before,"freeBytesAfter":free_after,"workBytes":work_bytes,"evidenceBytesBeforeReceipt":evidence_bytes},"nextGate":"slow solver-owned tip" if status=="PASS_FINAL_EFFECTOR_MESH_C1_STATIC" else "surface/obstacle interaction diagnosis","claimCeiling":spec["claimCeiling"]}; receipt["receiptHash"]=self_hash(receipt,"receiptHash"); write_exclusive(EVIDENCE/"receipt.json",receipt); write_exclusive(EVIDENCE/"work-manifest.json",manifest(WORK)); write_exclusive(EVIDENCE/"evidence-manifest.json",manifest(EVIDENCE,exclusions=("evidence-manifest.json","independent-audit.json")))
    print("RC6_FINAL_EFFECTOR_MESH_C1_RECEIPT="+canonical({"status":status,"slowTipUnlocked":receipt["slowTipUnlocked"],"receiptHash":receipt["receiptHash"],"metrics":result["metrics"]}))

if __name__=="__main__": main()
