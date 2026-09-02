#!/usr/bin/env python3
"""Independently audit C1 persisted Data-state Mesh reconstruction."""

import hashlib,json,subprocess
from pathlib import Path

RESEARCH=Path(__file__).resolve().parents[1]
RETAINED_WORK=Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-data-attempt-42"); RETAINED_EVIDENCE=RESEARCH/"experiments/physical-richness/RC6-2026-09-02-final-effector-data-attempt-42"; RETAINED_CACHE=RETAINED_WORK/"final-effector-plus1/mantaflow-cache"
FAILURE_EVIDENCE=RESEARCH/"experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-attempt-44"; FAILURE_WORK=Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-attempt-44")
WORK=Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c1-attempt-45"); EVIDENCE=RESEARCH/"experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-c1-attempt-45"; CELL_ID="final-effector-mesh-c1"
ADOPT_TOOL=RESEARCH/"scripts/run-rc6-liquid-final-effector-mesh-c1-adopt-scene.py"; MESH_TOOL=RESEARCH/"scripts/run-rc6-liquid-final-effector-mesh-c1-scene.py"; RUNNER=RESEARCH/"scripts/run-rc6-liquid-final-effector-mesh-c1.py"; AUDITOR=Path(__file__).resolve(); SPEC=RESEARCH/"specs/ai-native-studio-rc6-liquid-final-effector-mesh-c1-tool-freeze.v0.50.json"; BANNED={".exr",".png",".jpg",".jpeg",".mov",".mp4"}
def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"))
def self_hash(v,f): b=dict(v);b.pop(f,None);return hashlib.sha256(canonical(b).encode()).hexdigest()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def check(k,v,c): c[k]=bool(v)
def manifest(root,exclusions=()):
    ex=set(exclusions); files=[{"path":str(p.relative_to(root)),"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink() and str(p.relative_to(root)) not in ex];v={"schemaVersion":"bfs.rootManifest.v0.1","root":str(root),"files":files};v["manifestHash"]=self_hash(v,"manifestHash");return v
def data_files(): return sorted([f"config/config_{f:04d}.uni" for f in range(1,8)]+[f"data/fluid_data_{f:04d}.vdb" for f in range(1,8)])
def all_files(): return sorted(data_files()+[f"mesh/fluid_mesh_{f:04d}.bobj.gz" for f in range(1,8)])
def roster(root): return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
def data_manifest(root):
    files=[{"path":r,"bytes":(root/r).stat().st_size,"sha256":sha(root/r)} for r in data_files()];v={"schemaVersion":"bfs.rc6LiquidDataManifest.v0.1","files":files};v["manifestHash"]=self_hash(v,"manifestHash");return v
def signed_pass(result,t):
    for s in result["samples"]:
        pos=[x for x in s["components"] if x["signedVolumeCubicMeters"]>1e-12];neg=[x for x in s["components"] if x["signedVolumeCubicMeters"]<-1e-12]
        if len(pos)!=t["requiredPositiveWaterBodiesPerFrame"] or len(neg)>t["maximumNegativeNestedShellCount"] or any(x["nonManifoldEdgeCount"] for x in s["components"]):return False
        for inner in neg:
            outer=pos[0]
            if any(inner["boundsMinWorld"][a]<outer["boundsMinWorld"][a]-1e-7 or inner["boundsMaxWorld"][a]>outer["boundsMaxWorld"][a]+1e-7 for a in range(3)):return False
            if sum((inner["centroidWorld"][a]-outer["centroidWorld"][a])**2 for a in range(3))**0.5>t["maximumNestedCentroidSeparationMeters"]:return False
    return True
def main():
    audit_path=EVIDENCE/"independent-audit.json"
    if audit_path.exists():raise RuntimeError("C1 audit path not fresh")
    spec=read(SPEC);admission=read(EVIDENCE/"admission.json");adoption=read(EVIDENCE/"cells/adoption/result.json");result=read(EVIDENCE/f"cells/{CELL_ID}/result.json");receipt=read(EVIDENCE/"receipt.json");retained_data=data_manifest(RETAINED_CACHE);checks={}
    check("specSelfHash",spec.get("status")=="FROZEN" and spec.get("specHash")==self_hash(spec,"specHash"),checks)
    tools={str(ADOPT_TOOL.relative_to(RESEARCH)):sha(ADOPT_TOOL),str(MESH_TOOL.relative_to(RESEARCH)):sha(MESH_TOOL),str(RUNNER.relative_to(RESEARCH)):sha(RUNNER),str(AUDITOR.relative_to(RESEARCH)):sha(AUDITOR)};check("toolRosterExact",spec.get("tools")==tools,checks)
    check("retainedAcceptedExact",manifest(RETAINED_WORK)["manifestHash"]==spec["inputs"]["retainedWorkManifestHash"] and retained_data["manifestHash"]==spec["inputs"]["retainedDataManifestHash"] and read(RETAINED_EVIDENCE/"receipt.json")["receiptHash"]==spec["inputs"]["retainedReceiptHash"] and read(RETAINED_EVIDENCE/"independent-audit.json")["auditHash"]==spec["inputs"]["retainedAuditHash"],checks)
    check("retainedFailureExact",manifest(FAILURE_EVIDENCE)["manifestHash"]==spec["retainedFailure"]["evidenceRootManifestHash"] and manifest(FAILURE_WORK)["manifestHash"]==spec["retainedFailure"]["workRootManifestHash"] and read(FAILURE_EVIDENCE/"processes/01-final-effector-mesh.json")["processHash"]==spec["retainedFailure"]["processHash"],checks)
    check("admissionExact",admission["status"]=="PASS" and admission["admissionHash"]==self_hash(admission,"admissionHash") and admission["retainedDataManifestHash"]==retained_data["manifestHash"] and admission["retainedFailureProcessHash"]==spec["retainedFailure"]["processHash"],checks)
    procs=[read(EVIDENCE/f"processes/{i:02d}.json") for i in (1,2)]; logs_ok=True
    for i,p in enumerate(procs,1):
        out=EVIDENCE/f"logs/{i:02d}.stdout.log";err=EVIDENCE/f"logs/{i:02d}.stderr.log";logs_ok=logs_ok and p["processHash"]==self_hash(p,"processHash") and p["exitCode"]==0 and sha(out)==p["stdoutSha256"] and sha(err)==p["stderrSha256"] and err.stat().st_size==0
    check("processesAndLogsExact",logs_ok and "RC6_FINAL_EFFECTOR_DATA_ADOPT=" in (EVIDENCE/"logs/01.stdout.log").read_text() and "RC6_FINAL_EFFECTOR_MESH_C1=" in (EVIDENCE/"logs/02.stdout.log").read_text(),checks)
    check("adoptionExact",adoption["status"]=="ADOPTED" and adoption["resultHash"]==self_hash(adoption,"resultHash") and adoption["configuration"]["retainedDataManifestHash"]==retained_data["manifestHash"] and adoption["authority"]=={"cacheStateAdoptions":1,"fluidDataBakes":0,"fluidMeshBakes":0,"blendSaves":1,"renderCalls":0,"networkCalls":0,"engineRemoteWrites":0},checks)
    check("meshResultExact",result["schemaVersion"]=="bfs.rc6LiquidFinalEffectorMeshC1Cell.v0.1" and result["resultHash"]==self_hash(result,"resultHash") and result["configuration"]["meshParticleRadius"]==9.0 and result["configuration"]["meshConcaveUpper"]==3.5 and result["configuration"]["cupEffectorSurfaceDistanceCells"]==2.5,checks)
    check("dataAndCacheExact",data_manifest(WORK/CELL_ID/"mantaflow-cache")==retained_data and roster(WORK/CELL_ID/"mantaflow-cache")==all_files(),checks)
    t=spec["acceptanceThresholds"];m=result["metrics"];scientific=m["maximumAbsoluteSourceVolumeErrorFraction"]<=t["maximumAbsoluteSourceVolumeErrorFraction"] and m["maximumAbsoluteVolumeDriftFraction"]<=t["maximumAbsoluteTemporalDriftFraction"] and m["maximumOutsideCupInteriorPlusOneVoxelFraction"]<=t["maximumOutsideCupInteriorPlusOneVoxelFraction"] and m["maximumNonManifoldEdgeCount"]==0 and signed_pass(result,t)
    check("scientificVerdictRecomputed",receipt["status"]==("PASS_FINAL_EFFECTOR_MESH_C1_STATIC" if scientific else "FAIL_FINAL_EFFECTOR_MESH_C1_STATIC") and receipt["slowTipUnlocked"]==scientific and receipt["signedTopologyPass"]==signed_pass(result,t),checks)
    check("receiptAndCountsExact",receipt["receiptHash"]==self_hash(receipt,"receiptHash") and receipt["counts"]=={"blenderStarts":2,"cacheStateAdoptions":1,"fluidDataBakes":0,"fluidMeshBakes":1,"blendSaves":2,"renderCalls":0,"networkCalls":0,"engineRemoteWrites":0},checks)
    check("noSymlinkOrMedia",not any(p.is_symlink() for root in (WORK,EVIDENCE) for p in root.rglob("*")) and not any(p.is_file() and p.suffix.lower() in BANNED for root in (WORK,EVIDENCE) for p in root.rglob("*")),checks)
    check("manifestsExact",read(EVIDENCE/"work-manifest.json")==manifest(WORK) and read(EVIDENCE/"evidence-manifest.json")==manifest(EVIDENCE,exclusions=("evidence-manifest.json","independent-audit.json")),checks)
    committed=True
    for rel in list(spec["tools"])+[str(SPEC.relative_to(RESEARCH))]:
        shown=subprocess.run(["git","show",f"{admission['researchCommit']}:{rel}"],cwd=RESEARCH,capture_output=True);committed=committed and shown.returncode==0 and hashlib.sha256(shown.stdout).hexdigest()==sha(RESEARCH/rel)
    check("committedBytesExact",committed,checks)
    audit={"schemaVersion":"bfs.rc6LiquidFinalEffectorMeshC1IndependentAudit.v0.1","status":"PASS" if all(checks.values()) else "FAIL","scientificVerdict":receipt["status"],"checks":checks,"checksPassed":sum(checks.values()),"checksTotal":len(checks),"receiptHash":receipt["receiptHash"],"adoptionResultHash":adoption["resultHash"],"meshResultHash":result["resultHash"],"claimCeiling":spec["claimCeiling"]};audit["auditHash"]=self_hash(audit,"auditHash")
    with audit_path.open("x") as h:json.dump(audit,h,indent=2,sort_keys=True);h.write("\n")
    print(canonical({"status":audit["status"],"checks":f"{audit['checksPassed']}/{audit['checksTotal']}","scientificVerdict":audit["scientificVerdict"],"auditHash":audit["auditHash"]}))
    if audit["status"]!="PASS":raise RuntimeError("C1 audit failed")
if __name__=="__main__":main()
