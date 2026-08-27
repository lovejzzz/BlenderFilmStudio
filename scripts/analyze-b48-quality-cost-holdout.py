"""Analyze, attack and decide the preregistered B48 quality/cost holdout."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import statistics
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


AP1_LUMA=np.asarray([0.2722287168,0.6740817658,0.0536895174],dtype=np.float64)
RAW_ROSTER=["BFS_MASTER.Combined","BFS_MASTER.Depth","BFS_MASTER.Normal","BFS_MASTER.Vector","BFS_MASTER.CryptoObject00","BFS_MASTER.CryptoObject01","BFS_MASTER.CryptoObject02"]
NOISY="BFS_MASTER.Noisy Image"


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def read_exr(path):
    first=oiio.ImageBuf(str(path),0,0)
    if not first.initialized:raise RuntimeError(first.geterror())
    roster=[]; combined=None; channels=None
    for index in range(first.nsubimages):
        image=oiio.ImageBuf(str(path),index,0);spec=image.spec();name=str(spec.getattribute("oiio:subimagename") or f"subimage-{index}");roster.append(name)
        if name.endswith(".Combined"):combined=np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT),dtype="<f4"));channels=list(spec.channelnames)
    if combined is None or combined.shape!=(72,128,4):raise RuntimeError(f"invalid Combined shape: {path}")
    finite=bool(np.isfinite(combined).all());metadata={"name":"Combined","shape":list(combined.shape),"channels":channels,"dtype":"float32-le","order":"C"};header=json.dumps(metadata,sort_keys=True,separators=(",",":")).encode()+b"\n"
    return combined,roster,finite,hashlib.sha256(header+combined.tobytes(order="C")).hexdigest()


def edge_mask(reference_rgb):
    y=np.maximum(np.tensordot(reference_rgb.astype(np.float64),AP1_LUMA,axes=([2],[0])),0.0);dx=np.zeros_like(y);dy=np.zeros_like(y)
    dx[:,1:-1]=.5*(y[:,2:]-y[:,:-2]);dx[:,0]=y[:,1]-y[:,0];dx[:,-1]=y[:,-1]-y[:,-2];dy[1:-1,:]=.5*(y[2:,:]-y[:-2,:]);dy[0,:]=y[1,:]-y[0,:];dy[-1,:]=y[-1,:]-y[-2,:]
    magnitude=np.hypot(dx,dy);count=max(1,math.ceil(magnitude.size*.10));selected=np.argsort(-magnitude.reshape(-1),kind="stable")[:count];mask=np.zeros(magnitude.size,dtype=bool);mask[selected]=True
    return mask.reshape(magnitude.shape),count,float(magnitude.reshape(-1)[selected[-1]])


def metrics(candidate,target,mask,rms):
    a=candidate[...,:3].astype(np.float64);b=target[...,:3].astype(np.float64);delta=a-b;ay=np.maximum(np.tensordot(a,AP1_LUMA,axes=([2],[0])),0.0);by=np.maximum(np.tensordot(b,AP1_LUMA,axes=([2],[0])),0.0);linear=float(np.sqrt(np.mean(np.square(delta))))
    return {"linearNrmseByEnsembleRms":linear/rms,"logLuminanceRmse":float(np.sqrt(np.mean(np.square(np.log2(1+ay)-np.log2(1+by))))),"edgeLinearRmse":float(np.sqrt(np.mean(np.square(delta[mask])))),"linearRmse":linear,"linearMae":float(np.mean(np.abs(delta))),"linearP95AbsoluteError":float(np.percentile(np.abs(delta),95)),"linearMaxAbsoluteError":float(np.max(np.abs(delta)))}


def expected_runs(spec):return {f"{shot['id']}-{cell['id']}":(shot,cell) for shot in spec["shots"] for cell in [*spec["referenceCells"],*spec["candidateCells"]]}


def replay_selection(evidence,spec):
    summaries=[]
    for cell in spec["candidateCells"]:
        rows=[next(item for item in shot["candidates"] if item["cellId"]==cell["id"]) for shot in evidence["shots"]];eligible=all(row["passed"] for row in rows)
        render=[row["renderSeconds"] for row in rows];wall=[row["freshContainerWallSeconds"] for row in rows];sizes=[row["artifact"]["bytes"] for row in rows]
        summaries.append({"cellId":cell["id"],"samples":cell["samples"],"denoising":cell["denoising"],"eligible":eligible,"medianRenderSeconds":statistics.median(render),"meanRenderSeconds":statistics.mean(render),"meanFreshContainerWallSeconds":statistics.mean(wall),"meanExrBytes":statistics.mean(sizes),"projectedRenderSeconds240":statistics.mean(render)*spec["costProjection"]["frames"],"projectedExrBytes240":statistics.mean(sizes)*spec["costProjection"]["frames"]})
    eligible=[item for item in summaries if item["eligible"]];eligible.sort(key=lambda item:(item["medianRenderSeconds"],item["samples"],item["denoising"],item["cellId"]))
    return summaries,eligible[0]["cellId"] if eligible else None


def hash_payload(evidence):return {key:value for key,value in evidence.items() if key not in {"evidenceCoreHash","attacks","attacksPassed","verdict"}}


def validate(evidence,spec):
    if not all(item["match"] for item in evidence["parentObservations"]):return "PARENT_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"]):return "SOURCE_IDENTITY"
    if evidence["image"]!={"id":spec["image"]["id"],"os":spec["image"]["os"],"architecture":spec["image"]["architecture"],"sizeBytes":spec["image"]["dockerReportedSizeBytes"]} or evidence["hostInspector"]!=spec["hostInspector"]:return "IMAGE_IDENTITY"
    if evidence["securityBoundary"]!=spec["containerContract"]:return "SECURITY_BOUNDARY"
    if evidence["diskAdmission"]["status"]!="ACCEPTED":return "DISK_ADMISSION"
    expected=expected_runs(spec);observed={item["runId"]:item for item in evidence["runObservations"]}
    if set(observed)!=set(expected):return "CELL_ROSTER"
    for run_id,(shot,cell) in expected.items():
        item=observed[run_id];argv=item["argv"]
        def pair(flag,value):return any(argv[index:index+2]==[flag,str(value)] for index in range(len(argv)-1))
        if not all((pair('--platform',spec['containerContract']['platform']),pair('--network',spec['containerContract']['network']),pair('--user',spec['containerContract']['user']),pair('--cap-drop','ALL'),pair('--security-opt','no-new-privileges:true'),'--read-only' in argv,any('dst=/repo,readonly' in token for token in argv))):return "SECURITY_BOUNDARY"
        if item["samples"]!=cell["samples"]:return "SAMPLE_SETTING"
        if item["seedOffset"]!=cell["seedOffset"] or item["seed"]!=item["baseShotSeed"]+cell["seedOffset"]:return "SEED_SETTING"
        if item["denoising"]!=cell["denoising"] or (cell["denoising"] and (item["denoiser"]!="OPENIMAGEDENOISE" or item["denoisingInputPasses"]!="RGB_ALBEDO_NORMAL" or item["denoisingPrefilter"]!="ACCURATE")):return "DENOISER_SETTING"
        wanted=[*RAW_ROSTER,*([NOISY] if cell["denoising"] else [])]
        if item["roster"]!=wanted:return "PASS_ROSTER"
        if not item["allCombinedFinite"]:return "NON_FINITE"
    for shot in evidence["shots"]:
        if len({item["combinedCanonicalFloat32Sha256"] for item in shot["references"]})!=3:return "REFERENCE_DISTINCT"
        if any(not math.isfinite(value) or value<=0 for value in shot["referenceFloor"].values()):return "QUALITY_FLOOR"
        for item in shot["candidates"]:
            expected_pass=True
            for name,value in item["metricsAgainstEnsemble"].items():
                if name not in spec["qualityGate"]["metrics"]:continue
                ratio=value/shot["referenceFloor"][name]
                if not math.isfinite(value) or abs(ratio-item["floorMultiples"][name])>1e-12:return "METRIC_REPLAY"
                expected_pass=expected_pass and ratio<=spec["qualityGate"]["maximumFloorMultiple"]
            if item["passed"]!=expected_pass:return "METRIC_REPLAY"
    summaries,selected=replay_selection(evidence,spec)
    if evidence["candidateSummaries"]!=summaries or evidence["selectedCellId"]!=selected:return "SELECTION_REPLAY"
    counts=evidence["operationCounts"]
    if counts!={"dockerRuns":spec["operationBoundary"]["dockerRuns"],"hostExrAnalyses":spec["operationBoundary"]["hostExrAnalyses"],"builds":0,"pulls":0,"downloads":0,"modelCalls":0,"videoModelCalls":0}:return "OPERATION_BOUNDARY"
    if evidence["cleanup"]["experimentContainersRunningAfter"]!=0:return "CLEANUP"
    if evidence.get("evidenceCoreHash")!=canonical_hash(hash_payload(evidence)):return "EVIDENCE_SELF_HASH"
    return None


def attacks(evidence,spec):
    cases=[]
    def add(attack_id,expected,mutator):
        clone=copy.deepcopy(evidence);mutator(clone);clone["evidenceCoreHash"]=canonical_hash(hash_payload(clone)) if expected!="EVIDENCE_SELF_HASH" else "0"*64;observed=validate(clone,spec);cases.append({"id":attack_id,"expectedReason":expected,"observedReason":observed,"passed":observed==expected})
    add("A01_PARENT","PARENT_IDENTITY",lambda x:x["parentObservations"][0].update(match=False));add("A02_SOURCE","SOURCE_IDENTITY",lambda x:x["sourceObservations"][0].update(match=False));add("A03_IMAGE","IMAGE_IDENTITY",lambda x:x["image"].update(architecture="arm64"));add("A04_SECURITY","SECURITY_BOUNDARY",lambda x:x["securityBoundary"].update(network="bridge"));add("A05_DISK","DISK_ADMISSION",lambda x:x["diskAdmission"].update(status="BLOCKED"));add("A06_CELL_ROSTER","CELL_ROSTER",lambda x:x["runObservations"].pop());add("A07_SAMPLES","SAMPLE_SETTING",lambda x:x["runObservations"][0].update(samples=511));add("A08_SEED","SEED_SETTING",lambda x:x["runObservations"][0].update(seedOffset=1));add("A09_DENOISER","DENOISER_SETTING",lambda x:next(item for item in x["runObservations"] if item["denoising"]).update(denoiser="NONE"));add("A10_PASS_ROSTER","PASS_ROSTER",lambda x:x["runObservations"][0]["roster"].pop());add("A11_NON_FINITE","NON_FINITE",lambda x:x["runObservations"][0].update(allCombinedFinite=False));add("A12_REFERENCE_DISTINCT","REFERENCE_DISTINCT",lambda x:x["shots"][0]["references"][1].update(combinedCanonicalFloat32Sha256=x["shots"][0]["references"][0]["combinedCanonicalFloat32Sha256"]));add("A13_FLOOR","QUALITY_FLOOR",lambda x:x["shots"][0]["referenceFloor"].update(linearNrmseByEnsembleRms=0));add("A14_METRIC","METRIC_REPLAY",lambda x:x["shots"][0]["candidates"][0]["floorMultiples"].update(linearNrmseByEnsembleRms=999));add("A15_SELECTION","SELECTION_REPLAY",lambda x:x.update(selectedCellId="UNREGISTERED"));add("A16_OPERATIONS","OPERATION_BOUNDARY",lambda x:x["operationCounts"].update(dockerRuns=15));add("A17_CLEANUP","CLEANUP",lambda x:x["cleanup"].update(experimentContainersRunningAfter=1));add("A18_HASH","EVIDENCE_SELF_HASH",lambda x:None)
    return cases


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--spec",type=Path,required=True);parser.add_argument("--receipt",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args();spec=json.loads(args.spec.read_text());receipt=json.loads(args.receipt.read_text());root=args.receipt.parent
    arrays={};run_observations=[]
    for run in receipt["runs"]:
        report=run["report"];path=root/run["runId"]/report["artifact"]["uri"];pixels,roster,finite,combined_hash=read_exr(path);arrays[run["runId"]]=pixels;settings=report["settings"]
        run_observations.append({"runId":run["runId"],"shotId":run["shotId"],"cellId":run["cellId"],"argv":run["argv"],"samples":settings["samples"],"denoising":settings["denoising"],"denoiser":settings["denoiser"],"denoisingInputPasses":settings["denoisingInputPasses"],"denoisingPrefilter":settings["denoisingPrefilter"],"baseShotSeed":report["bindings"]["baseShotSeed"],"seedOffset":settings["seedOffset"],"seed":settings["seed"],"roster":roster,"allCombinedFinite":finite,"combinedCanonicalFloat32Sha256":combined_hash,"renderSeconds":report["renderSeconds"],"freshContainerWallSeconds":run["elapsedMs"]/1000,"artifact":{"uri":str(path.relative_to(root.parent.parent)),"sha256":sha256_file(path),"bytes":path.stat().st_size},"sourceSha256":report["source"]["sha256"],"imageId":run["imageId"]})
    shots=[]
    for shot_spec in spec["shots"]:
        refs=[]
        for cell in spec["referenceCells"]:
            item=next(value for value in run_observations if value["runId"]==f"{shot_spec['id']}-{cell['id']}");refs.append(item)
        ensemble=np.mean(np.stack([arrays[item["runId"]].astype(np.float64) for item in refs]),axis=0);rms=float(np.sqrt(np.mean(np.square(ensemble[...,:3]))));mask,count,cutoff=edge_mask(ensemble[...,:3]);ref_metrics=[]
        for item in refs:ref_metrics.append({**item,"metricsAgainstEnsemble":metrics(arrays[item["runId"]],ensemble,mask,rms)})
        floor={name:max(item["metricsAgainstEnsemble"][name] for item in ref_metrics) for name in spec["qualityGate"]["metrics"]};candidates=[]
        for cell in spec["candidateCells"]:
            item=next(value for value in run_observations if value["runId"]==f"{shot_spec['id']}-{cell['id']}");measured=metrics(arrays[item["runId"]],ensemble,mask,rms);multiples={name:measured[name]/floor[name] for name in spec["qualityGate"]["metrics"]};passed=all(value<=spec["qualityGate"]["maximumFloorMultiple"] for value in multiples.values());candidates.append({**item,"metricsAgainstEnsemble":measured,"floorMultiples":multiples,"passed":passed})
        shots.append({"id":shot_spec["id"],"shotId":shot_spec["shotId"],"frame":shot_spec["frame"],"ensembleMean":{"dtype":"float64-le","shape":list(ensemble.shape),"sha256":hashlib.sha256(np.ascontiguousarray(ensemble.astype("<f8")).tobytes()).hexdigest(),"rgbRms":rms},"edgeMask":{"pixelCount":count,"gradientCutoff":cutoff},"referenceFloor":floor,"references":ref_metrics,"candidates":candidates})
    operation_counts={"dockerRuns":sum(item.startswith("DOCKER_RUN_") for item in receipt["runtimeOperations"]),"hostExrAnalyses":sum(item.startswith("HOST_EXR_ANALYSIS_") for item in receipt["runtimeOperations"]),"builds":0,"pulls":0,"downloads":0,"modelCalls":0,"videoModelCalls":0}
    evidence={"schemaVersion":"bfs.codexWorkerQualityCostHoldoutEvidence.v0.1","experimentId":"B48","preregistration":receipt["preregistration"],"toolFreezeCommit":receipt["toolFreezeCommit"],"tools":receipt["tools"],"hostInspector":receipt["hostInspectorObservation"],"parents":receipt["parents"],"parentObservations":receipt["parentObservations"],"sourceObservations":receipt["sourceObservations"],"image":receipt["image"],"diskAdmission":receipt["diskAdmission"],"securityBoundary":receipt["securityBoundary"],"qualityGate":spec["qualityGate"],"runObservations":run_observations,"shots":shots,"operationCounts":operation_counts,"cleanup":receipt["cleanup"],"nonClaims":spec["nonClaims"]}
    summaries,selected=replay_selection(evidence,spec);evidence["candidateSummaries"]=summaries;evidence["selectedCellId"]=selected;evidence["evidenceCoreHash"]=canonical_hash(hash_payload(evidence));base_failure=validate(evidence,spec);evidence["attacks"]=attacks(evidence,spec);evidence["attacksPassed"]=sum(item["passed"] for item in evidence["attacks"]);valid=base_failure is None and evidence["attacksPassed"]==len(spec["attacks"]);evidence["verdict"]=spec["invalidVerdict"] if not valid else spec["acceptedVerdict"] if selected else spec["noPointVerdict"]
    args.output.write_text(json.dumps(evidence,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8");print(f"BFS_B48_RESULT verdict={evidence['verdict']} selected={selected or 'none'} attacks={evidence['attacksPassed']}/{len(evidence['attacks'])}",flush=True)


if __name__=="__main__":main()
