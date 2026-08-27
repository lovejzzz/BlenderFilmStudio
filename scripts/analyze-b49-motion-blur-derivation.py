"""Analyze B49-MB-D1 motion-blur semantics, pass changes and cost."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


RAW_ROSTER=["BFS_MASTER.Combined","BFS_MASTER.Depth","BFS_MASTER.Normal","BFS_MASTER.Vector","BFS_MASTER.CryptoObject00","BFS_MASTER.CryptoObject01","BFS_MASTER.CryptoObject02"]
AP1_LUMA=np.asarray([0.2722287168,0.6740817658,0.0536895174],dtype=np.float64)


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
        finite=bool(np.isfinite(pixels).all());metadata={"name":name,"shape":list(pixels.shape),"channels":list(spec.channelnames),"dtype":"float32-le","order":"C"};header=json.dumps(metadata,sort_keys=True,separators=(",",":")).encode()+b"\n";passes[name]={"pixels":pixels,"shape":list(pixels.shape),"channels":list(spec.channelnames),"finite":finite,"canonicalFloat32Sha256":hashlib.sha256(header+pixels.tobytes(order="C")).hexdigest()}
    return roster,passes


def edge_energy(combined):
    rgb=combined[...,:3].astype(np.float64);y=np.tensordot(rgb,AP1_LUMA,axes=([2],[0]));dx=np.diff(y,axis=1);dy=np.diff(y,axis=0);return {"horizontalRms":float(np.sqrt(np.mean(np.square(dx)))),"verticalRms":float(np.sqrt(np.mean(np.square(dy)))),"combinedRms":float(np.sqrt((np.mean(np.square(dx))+np.mean(np.square(dy)))/2))}


def compare(left,right):
    rows={}
    for name in RAW_ROSTER:
        a=left[name]["pixels"];b=right[name]["pixels"];delta=np.subtract(a,b,dtype=np.float32);absolute=np.abs(delta.astype(np.float64));rows[name]={"exact":bool(np.array_equal(a,b)),"changedFloatComponents":int(np.count_nonzero(delta)),"rmse":float(np.sqrt(np.mean(np.square(delta.astype(np.float64))))),"mae":float(np.mean(absolute)),"maxAbsoluteError":float(np.max(absolute))}
    return rows


def hash_payload(evidence):return {key:value for key,value in evidence.items() if key not in {"evidenceCoreHash","status","baseFailure"}}


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
        item=observed[cell_id];render=spec["render"]
        if item["frame"]!=cell["frame"] or item["shotId"]!=cell["shot"]:return "CELL_SETTING"
        if item["resolution"]!=[*render["resolution"],100] or item["samples"]!=render["samples"] or item["seedOffset"]!=render["seedOffset"] or item["seed"]!=item["baseShotSeed"]+render["seedOffset"] or item["denoising"]!=render["denoising"] or item["persistentData"]!=render["persistentData"] or item["threads"]!=render["threads"]:return "RENDER_SETTING"
        if item["motionBlur"]!=cell["enabled"] or item["motionBlurShutter"]!=cell["shutter"] or item["motionBlurPosition"]!=cell["position"]:return "MOTION_BLUR_SETTING"
        if item["roster"]!=RAW_ROSTER:return "PASS_ROSTER"
        if not all(value["finite"] for value in item["passes"].values()):return "NON_FINITE"
    if [item["id"] for item in evidence["relations"]]!=[item["id"] for item in spec["frozenRelations"]]:return "RELATION_ROSTER"
    expected_counts={key:spec["operationBoundary"][key] for key in ("dockerRuns","hostExrAnalyses","builds","pulls","downloads","modelCalls","videoModelCalls")}
    if evidence["operationCounts"]!=expected_counts:return "OPERATION_BOUNDARY"
    if evidence["cleanup"]["experimentContainersRunningAfter"]!=0:return "CLEANUP"
    if evidence.get("evidenceCoreHash")!=canonical_hash(hash_payload(evidence)):return "EVIDENCE_SELF_HASH"
    return None


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--spec",type=Path,required=True);parser.add_argument("--receipt",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args();spec=json.loads(args.spec.read_text());receipt=json.loads(args.receipt.read_text());root=args.receipt.parent;arrays={};observations=[]
    for run in receipt["runs"]:
        report=run["report"];cell=next(item for item in spec["cells"] if item["id"]==run["runId"]);path=root/run["runId"]/report["artifact"]["uri"];roster,passes=read_exr(path,*spec["render"]["resolution"]);arrays[run["runId"]]=passes;settings=report["settings"];pass_summary={name:{key:value for key,value in data.items() if key!="pixels"} for name,data in passes.items()};combined=passes["BFS_MASTER.Combined"]["pixels"]
        observations.append({"cellId":cell["id"],"shotId":cell["shot"],"frame":cell["frame"],"role":cell["role"],"argv":run["argv"],"baseShotSeed":report["bindings"]["baseShotSeed"],"resolution":settings["resolution"],"samples":settings["samples"],"seedOffset":settings["seedOffset"],"seed":settings["seed"],"denoising":settings["denoising"],"motionBlur":settings["motionBlur"],"motionBlurShutter":settings["motionBlurShutter"],"motionBlurPosition":settings["motionBlurPosition"],"persistentData":settings["persistentData"],"threads":settings["threads"],"camera":report["camera"],"renderSeconds":report["renderSeconds"],"saveSeconds":report["saveSeconds"],"freshContainerWallSeconds":run["elapsedMs"]/1000,"peakSelfRssKiB":report["peakSelfRssKiB"],"combinedEdgeEnergy":edge_energy(combined),"roster":roster,"passes":pass_summary,"artifact":{"uri":str(path.relative_to(root.parent.parent)),"sha256":sha256_file(path),"bytes":path.stat().st_size}})
    by_id={item["cellId"]:item for item in observations};relations=[]
    for relation in spec["frozenRelations"]:
        if "left" in relation:
            left,right=relation["left"],relation["right"];relations.append({"id":relation["id"],"question":relation["question"],"left":left,"right":right,"passComparisons":compare(arrays[left],arrays[right]),"combinedEdgeEnergy":{"left":by_id[left]["combinedEdgeEnergy"],"right":by_id[right]["combinedEdgeEnergy"]},"cost":{"renderSecondsRatio":by_id[right]["renderSeconds"]/by_id[left]["renderSeconds"],"freshContainerWallSecondsRatio":by_id[right]["freshContainerWallSeconds"]/by_id[left]["freshContainerWallSeconds"],"exrBytesRatio":by_id[right]["artifact"]["bytes"]/by_id[left]["artifact"]["bytes"]}})
        else:
            baseline=relation["members"][0];rows=[]
            for member in relation["members"]:
                rows.append({"cellId":member,"versusBaseline":compare(arrays[baseline],arrays[member]),"combinedEdgeEnergy":by_id[member]["combinedEdgeEnergy"],"renderSeconds":by_id[member]["renderSeconds"],"freshContainerWallSeconds":by_id[member]["freshContainerWallSeconds"],"peakSelfRssKiB":by_id[member]["peakSelfRssKiB"],"exrBytes":by_id[member]["artifact"]["bytes"]})
            relations.append({"id":relation["id"],"question":relation["question"],"baseline":baseline,"members":relation["members"],"rows":rows})
    operation_counts={"dockerRuns":sum(item.startswith("DOCKER_RUN_") for item in receipt["runtimeOperations"]),"hostExrAnalyses":sum(item.startswith("HOST_EXR_ANALYSIS_") for item in receipt["runtimeOperations"]),"builds":0,"pulls":0,"downloads":0,"modelCalls":0,"videoModelCalls":0}
    evidence={"schemaVersion":"bfs.motionBlurDerivationAnalysis.v0.1","experimentId":spec["experimentId"],"preregistration":receipt["preregistration"],"toolFreezeCommit":receipt["toolFreezeCommit"],"tools":receipt["tools"],"runtime":{"python":platform.python_version(),"openImageIO":oiio.VERSION_STRING,"numpy":np.__version__},"parents":receipt["parents"],"parentObservations":receipt["parentObservations"],"sourceObservations":receipt["sourceObservations"],"image":receipt["image"],"hostInspector":receipt["hostInspectorObservation"],"diskAdmission":receipt["diskAdmission"],"securityBoundary":receipt["securityBoundary"],"observations":observations,"relations":relations,"operationCounts":operation_counts,"cleanup":receipt["cleanup"],"nonClaims":spec["nonClaims"]};evidence["evidenceCoreHash"]=canonical_hash(hash_payload(evidence));failure=validate(evidence,spec);evidence["baseFailure"]=failure;evidence["status"]=spec["usableStatus"] if failure is None else spec["invalidStatus"];args.output.write_text(json.dumps(evidence,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8");print(f"BFS_B49_MB_D1_ANALYSIS status={evidence['status']} failure={failure or 'none'} cells={len(observations)} relations={len(relations)}",flush=True)


if __name__=="__main__":main()
