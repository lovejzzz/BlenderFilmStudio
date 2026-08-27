"""Analyze, attack and decide the formal B49-MB holdout."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


AP1_LUMA=np.asarray([0.2722287168,0.6740817658,0.0536895174],dtype=np.float64)
RAW_ROSTER=["BFS_MASTER.Combined","BFS_MASTER.Depth","BFS_MASTER.Normal","BFS_MASTER.Vector","BFS_MASTER.CryptoObject00","BFS_MASTER.CryptoObject01","BFS_MASTER.CryptoObject02"]


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def read_exr(path,width,height):
    first=oiio.ImageBuf(str(path),0,0)
    if not first.initialized:raise RuntimeError(first.geterror())
    roster=[];passes={}
    for index in range(first.nsubimages):
        image=oiio.ImageBuf(str(path),index,0);spec=image.spec();name=str(spec.getattribute("oiio:subimagename") or f"subimage-{index}");pixels=np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT),dtype="<f4"));roster.append(name)
        if pixels.shape[0:2]!=(height,width):raise RuntimeError(f"invalid pass shape: {name} {pixels.shape}")
        metadata={"name":name,"shape":list(pixels.shape),"channels":list(spec.channelnames),"dtype":"float32-le","order":"C"};header=json.dumps(metadata,sort_keys=True,separators=(",",":")).encode()+b"\n";passes[name]={"pixels":pixels,"shape":list(pixels.shape),"channels":list(spec.channelnames),"finite":bool(np.isfinite(pixels).all()),"canonicalFloat32Sha256":hashlib.sha256(header+pixels.tobytes(order="C")).hexdigest()}
    return roster,passes


def edge_mask(reference_rgb):
    y=np.maximum(np.tensordot(reference_rgb.astype(np.float64),AP1_LUMA,axes=([2],[0])),0.0);dx=np.zeros_like(y);dy=np.zeros_like(y);dx[:,1:-1]=.5*(y[:,2:]-y[:,:-2]);dx[:,0]=y[:,1]-y[:,0];dx[:,-1]=y[:,-1]-y[:,-2];dy[1:-1,:]=.5*(y[2:,:]-y[:-2,:]);dy[0,:]=y[1,:]-y[0,:];dy[-1,:]=y[-1,:]-y[-2,:];magnitude=np.hypot(dx,dy);count=max(1,math.ceil(magnitude.size*.10));selected=np.argsort(-magnitude.reshape(-1),kind="stable")[:count];mask=np.zeros(magnitude.size,dtype=bool);mask[selected]=True;return mask.reshape(magnitude.shape),count,float(magnitude.reshape(-1)[selected[-1]])


def metrics(candidate,target,mask,rms):
    a=candidate[...,:3].astype(np.float64);b=target[...,:3].astype(np.float64);delta=a-b;ay=np.maximum(np.tensordot(a,AP1_LUMA,axes=([2],[0])),0.0);by=np.maximum(np.tensordot(b,AP1_LUMA,axes=([2],[0])),0.0);linear=float(np.sqrt(np.mean(np.square(delta))));return {"linearNrmseByEnsembleRms":linear/rms,"logLuminanceRmse":float(np.sqrt(np.mean(np.square(np.log2(1+ay)-np.log2(1+by))))),"edgeLinearRmse":float(np.sqrt(np.mean(np.square(delta[mask])))),"linearRmse":linear,"linearMae":float(np.mean(np.abs(delta))),"linearP95AbsoluteError":float(np.percentile(np.abs(delta),95)),"linearMaxAbsoluteError":float(np.max(np.abs(delta)))}


def domain_compare(left,right):
    return {name:{"exact":bool(np.array_equal(left[name]["pixels"],right[name]["pixels"])),"changedFloatComponents":int(np.count_nonzero(np.subtract(left[name]["pixels"],right[name]["pixels"],dtype=np.float32))),"leftHash":left[name]["canonicalFloat32Sha256"],"rightHash":right[name]["canonicalFloat32Sha256"]} for name in RAW_ROSTER}


def decide(evidence,spec):
    if not evidence["quality"]["candidatePassed"]:return spec["rejectedVerdict"]
    if evidence["quality"]["candidateCloserMetricCount"]>=spec["qualityGate"]["minimumMetricsWhereCandidateStrictlyCloserThanNegativeControl"]:return spec["acceptedVerdict"]
    return spec["indistinguishableVerdict"]


def hash_payload(evidence):return {key:value for key,value in evidence.items() if key not in {"evidenceCoreHash","attacks","attacksPassed"}}


def validate(evidence,spec):
    if not all(item["match"] for item in evidence["parentObservations"]):return "PARENT_IDENTITY"
    if not all(item["match"] for item in evidence["sourceObservations"]):return "SOURCE_IDENTITY"
    expected_image={"id":spec["image"]["id"],"os":spec["image"]["os"],"architecture":spec["image"]["architecture"],"sizeBytes":spec["image"]["dockerReportedSizeBytes"]}
    if evidence["image"]!=expected_image:return "IMAGE_IDENTITY"
    if evidence["securityBoundary"]!=spec["containerContract"]:return "SECURITY_BOUNDARY"
    if evidence["diskAdmission"]["status"]!="ACCEPTED":return "DISK_ADMISSION"
    expected={cell["id"]:cell for cell in spec["cells"]};observed={item["cellId"]:item for item in evidence["observations"]}
    if list(observed)!=list(expected):return "CELL_ROSTER"
    for cell_id,cell in expected.items():
        item=observed[cell_id]
        if item["samples"]!=cell["samples"]:return "SAMPLE_SETTING"
        if item["seedOffset"]!=cell["seedOffset"] or item["seed"]!=item["baseShotSeed"]+cell["seedOffset"]:return "SEED_SETTING"
        if item["motionBlur"]!=cell["motionBlur"] or item["motionBlurShutter"]!=cell["shutter"] or item["motionBlurPosition"]!=cell["position"]:return "MOTION_BLUR_SETTING"
        if item["roster"]!=RAW_ROSTER:return "PASS_ROSTER"
        if not all(value["finite"] for value in item["passes"].values()):return "NON_FINITE"
    refs=evidence["quality"]["references"]
    if len({item["combinedCanonicalFloat32Sha256"] for item in refs})!=spec["qualityGate"]["referenceCount"]:return "REFERENCE_DISTINCT"
    if any(not math.isfinite(value) or value<=0 for value in evidence["quality"]["referenceFloor"].values()):return "QUALITY_FLOOR"
    quality=evidence["quality"];gate=spec["qualityGate"];metric_names=gate["metrics"]
    expected_multiples={name:quality["candidateMetrics"][name]/quality["referenceFloor"][name] for name in metric_names}
    if any(abs(expected_multiples[name]-quality["candidateFloorMultiples"][name])>1e-12 for name in metric_names):return "METRIC_REPLAY"
    expected_pass=all(value<=gate["maximumFloorMultiple"] for value in expected_multiples.values());expected_closer=[name for name in metric_names if quality["candidateMetrics"][name]<quality["negativeControlMetrics"][name]]
    if quality["candidatePassed"]!=expected_pass or quality["candidateCloserMetrics"]!=expected_closer or quality["candidateCloserMetricCount"]!=len(expected_closer):return "METRIC_REPLAY"
    domains=evidence["passDomains"];pd=spec["passDomainGate"]
    for relation in (domains["movingZeroVsOff"],domains["staticOnVsOff"]):
        if any(not relation[name]["exact"] for name in [*pd["imageContinuousPasses"],*pd["identifierPasses"]]) or relation[pd["modeDependentPasses"][0]]["exact"]:return "PASS_DOMAIN"
    if evidence["verdict"]!=decide(evidence,spec):return "VERDICT_REPLAY"
    expected_counts={key:spec["operationBoundary"][key] for key in ("dockerRuns","hostExrAnalyses","builds","pulls","downloads","modelCalls","videoModelCalls")}
    if evidence["operationCounts"]!=expected_counts:return "OPERATION_BOUNDARY"
    if evidence["cleanup"]["experimentContainersRunningAfter"]!=0:return "CLEANUP"
    if evidence.get("evidenceCoreHash")!=canonical_hash(hash_payload(evidence)):return "EVIDENCE_SELF_HASH"
    return None


def attacks(evidence,spec):
    cases=[]
    def add(attack_id,expected,mutator):
        clone=copy.deepcopy(evidence);mutator(clone);clone["evidenceCoreHash"]=canonical_hash(hash_payload(clone)) if expected!="EVIDENCE_SELF_HASH" else "0"*64;observed=validate(clone,spec);cases.append({"id":attack_id,"expectedReason":expected,"observedReason":observed,"passed":observed==expected})
    add("A01_PARENT","PARENT_IDENTITY",lambda x:x["parentObservations"][0].update(match=False));add("A02_SOURCE","SOURCE_IDENTITY",lambda x:x["sourceObservations"][0].update(match=False));add("A03_IMAGE","IMAGE_IDENTITY",lambda x:x["image"].update(architecture="arm64"));add("A04_SECURITY","SECURITY_BOUNDARY",lambda x:x["securityBoundary"].update(network="bridge"));add("A05_DISK","DISK_ADMISSION",lambda x:x["diskAdmission"].update(status="BLOCKED"));add("A06_CELLS","CELL_ROSTER",lambda x:x["observations"].pop());add("A07_SAMPLES","SAMPLE_SETTING",lambda x:x["observations"][0].update(samples=511));add("A08_SEED","SEED_SETTING",lambda x:x["observations"][0].update(seedOffset=1));add("A09_BLUR","MOTION_BLUR_SETTING",lambda x:x["observations"][0].update(motionBlur=False));add("A10_ROSTER","PASS_ROSTER",lambda x:x["observations"][0]["roster"].pop());add("A11_FINITE","NON_FINITE",lambda x:x["observations"][0]["passes"]["BFS_MASTER.Combined"].update(finite=False));add("A12_REFERENCES","REFERENCE_DISTINCT",lambda x:x["quality"]["references"][1].update(combinedCanonicalFloat32Sha256=x["quality"]["references"][0]["combinedCanonicalFloat32Sha256"]));add("A13_FLOOR","QUALITY_FLOOR",lambda x:x["quality"]["referenceFloor"].update(linearNrmseByEnsembleRms=0));add("A14_METRIC","METRIC_REPLAY",lambda x:x["quality"]["candidateFloorMultiples"].update(linearNrmseByEnsembleRms=999));add("A15_DOMAIN","PASS_DOMAIN",lambda x:x["passDomains"]["staticOnVsOff"]["BFS_MASTER.Vector"].update(exact=True));add("A16_VERDICT","VERDICT_REPLAY",lambda x:x.update(verdict=spec["invalidVerdict"]));add("A17_OPERATIONS","OPERATION_BOUNDARY",lambda x:x["operationCounts"].update(dockerRuns=9));add("A18_CLEANUP","CLEANUP",lambda x:x["cleanup"].update(experimentContainersRunningAfter=1));add("A19_HASH","EVIDENCE_SELF_HASH",lambda x:None);return cases


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--spec",type=Path,required=True);parser.add_argument("--receipt",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args();spec=json.loads(args.spec.read_text());receipt=json.loads(args.receipt.read_text());root=args.receipt.parent;arrays={};observations=[]
    for run in receipt["runs"]:
        cell=next(item for item in spec["cells"] if item["id"]==run["runId"]);report=run["report"];path=root/run["runId"]/report["artifact"]["uri"];roster,passes=read_exr(path,*spec["render"]["resolution"]);arrays[cell["id"]]=passes;settings=report["settings"];observations.append({"cellId":cell["id"],"shotId":cell["shot"],"frame":report["frame"],"role":cell["role"],"argv":run["argv"],"baseShotSeed":report["bindings"]["baseShotSeed"],"samples":settings["samples"],"seedOffset":settings["seedOffset"],"seed":settings["seed"],"motionBlur":settings["motionBlur"],"motionBlurShutter":settings["motionBlurShutter"],"motionBlurPosition":settings["motionBlurPosition"],"renderSeconds":report["renderSeconds"],"freshContainerWallSeconds":run["elapsedMs"]/1000,"peakSelfRssKiB":report["peakSelfRssKiB"],"roster":roster,"passes":{name:{key:value for key,value in data.items() if key!="pixels"} for name,data in passes.items()},"artifact":{"uri":str(path.relative_to(root.parent.parent)),"sha256":sha256_file(path),"bytes":path.stat().st_size}})
    ref_ids=[item["id"] for item in spec["cells"] if item["role"]=="reference"];reference_arrays=[arrays[cell_id]["BFS_MASTER.Combined"]["pixels"] for cell_id in ref_ids];ensemble=np.mean(np.stack([value.astype(np.float64) for value in reference_arrays]),axis=0);rms=float(np.sqrt(np.mean(np.square(ensemble[...,:3]))));mask,count,cutoff=edge_mask(ensemble[...,:3]);reference_rows=[]
    for cell_id,pixels in zip(ref_ids,reference_arrays):reference_rows.append({"cellId":cell_id,"combinedCanonicalFloat32Sha256":arrays[cell_id]["BFS_MASTER.Combined"]["canonicalFloat32Sha256"],"metricsAgainstEnsemble":metrics(pixels,ensemble,mask,rms)})
    metric_names=spec["qualityGate"]["metrics"];floor={name:max(item["metricsAgainstEnsemble"][name] for item in reference_rows) for name in metric_names};candidate_id=spec["qualityGate"]["candidate"];negative_id=spec["qualityGate"]["negativeControl"];candidate_metrics=metrics(arrays[candidate_id]["BFS_MASTER.Combined"]["pixels"],ensemble,mask,rms);negative_metrics=metrics(arrays[negative_id]["BFS_MASTER.Combined"]["pixels"],ensemble,mask,rms);multiples={name:candidate_metrics[name]/floor[name] for name in metric_names};candidate_passed=all(value<=spec["qualityGate"]["maximumFloorMultiple"] for value in multiples.values());closer=[name for name in metric_names if candidate_metrics[name]<negative_metrics[name]]
    quality={"ensemble":{"dtype":"float64-le","shape":list(ensemble.shape),"sha256":hashlib.sha256(np.ascontiguousarray(ensemble.astype("<f8")).tobytes()).hexdigest(),"rgbRms":rms},"edgeMask":{"pixelCount":count,"gradientCutoff":cutoff},"references":reference_rows,"referenceFloor":floor,"candidateCellId":candidate_id,"candidateMetrics":candidate_metrics,"candidateFloorMultiples":multiples,"candidatePassed":candidate_passed,"negativeControlCellId":negative_id,"negativeControlMetrics":negative_metrics,"candidateCloserMetrics":closer,"candidateCloserMetricCount":len(closer)}
    pass_domains={"movingZeroVsOff":domain_compare(arrays["T_C128_OFF"],arrays["T_C128_ZERO"]),"staticOnVsOff":domain_compare(arrays["I_C128_OFF"],arrays["I_C128_ON"])};operation_counts={"dockerRuns":sum(item.startswith("DOCKER_RUN_") for item in receipt["runtimeOperations"]),"hostExrAnalyses":sum(item.startswith("HOST_EXR_ANALYSIS_") for item in receipt["runtimeOperations"]),"builds":0,"pulls":0,"downloads":0,"modelCalls":0,"videoModelCalls":0}
    evidence={"schemaVersion":"bfs.codexWorkerMotionBlurHoldoutEvidence.v0.1","experimentId":spec["experimentId"],"preregistration":receipt["preregistration"],"toolFreezeCommit":receipt["toolFreezeCommit"],"tools":receipt["tools"],"runtime":{"python":platform.python_version(),"openImageIO":oiio.VERSION_STRING,"numpy":np.__version__},"parents":receipt["parents"],"parentObservations":receipt["parentObservations"],"sourceObservations":receipt["sourceObservations"],"image":receipt["image"],"hostInspector":receipt["hostInspectorObservation"],"diskAdmission":receipt["diskAdmission"],"securityBoundary":receipt["securityBoundary"],"observations":observations,"quality":quality,"passDomains":pass_domains,"operationCounts":operation_counts,"cleanup":receipt["cleanup"],"nonClaims":spec["nonClaims"],"baseFailure":None};evidence["verdict"]=decide(evidence,spec);evidence["evidenceCoreHash"]=canonical_hash(hash_payload(evidence));failure=validate(evidence,spec);evidence["baseFailure"]=failure
    if failure is not None:evidence["verdict"]=spec["invalidVerdict"]
    evidence["evidenceCoreHash"]=canonical_hash(hash_payload(evidence));failure=validate(evidence,spec);evidence["baseFailure"]=failure;evidence["attacks"]=attacks(evidence,spec);evidence["attacksPassed"]=sum(item["passed"] for item in evidence["attacks"])
    if failure is not None or evidence["attacksPassed"]!=len(spec["attacks"]):
        evidence["verdict"]=spec["invalidVerdict"];evidence["evidenceCoreHash"]=canonical_hash(hash_payload(evidence))
    args.output.write_text(json.dumps(evidence,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8");print(f"BFS_B49_MB_RESULT verdict={evidence['verdict']} candidatePass={candidate_passed} closer={len(closer)}/3 attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={failure or 'none'}",flush=True)


if __name__=="__main__":main()
