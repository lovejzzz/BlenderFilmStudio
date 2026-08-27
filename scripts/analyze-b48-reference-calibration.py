"""Calibrate the B48 quality metrics against three independent 512-spp replicas."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import platform
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


AP1_LUMA = np.asarray([0.2722287168, 0.6740817658, 0.0536895174], dtype=np.float64)
EXPECTED_ROSTER = [
    "BFS_MASTER.Combined", "BFS_MASTER.Depth", "BFS_MASTER.Normal", "BFS_MASTER.Vector",
    "BFS_MASTER.CryptoObject00", "BFS_MASTER.CryptoObject01", "BFS_MASTER.CryptoObject02",
]


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_combined(path, allow_noisy=False):
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror())
    roster = []
    pixels = None
    channels = None
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        roster.append(name)
        if name.endswith(".Combined"):
            pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
            channels = list(spec.channelnames)
    allowed_rosters = [EXPECTED_ROSTER]
    if allow_noisy:
        allowed_rosters.append([*EXPECTED_ROSTER, "BFS_MASTER.Noisy Image"])
    if roster not in allowed_rosters:
        raise RuntimeError(f"unexpected subimage roster in {path}: {roster}")
    if pixels is None or pixels.shape != (72, 128, 4) or not np.isfinite(pixels).all():
        raise RuntimeError(f"invalid Combined in {path}")
    metadata = {"name": "Combined", "shape": list(pixels.shape), "channels": channels, "dtype": "float32-le", "order": "C"}
    header = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    return pixels, roster, hashlib.sha256(header + pixels.tobytes(order="C")).hexdigest()


def edge_mask(reference_rgb):
    luma = np.maximum(np.tensordot(reference_rgb.astype(np.float64), AP1_LUMA, axes=([2], [0])), 0.0)
    dx = np.zeros_like(luma); dy = np.zeros_like(luma)
    dx[:, 1:-1] = 0.5 * (luma[:, 2:] - luma[:, :-2]); dx[:, 0] = luma[:, 1] - luma[:, 0]; dx[:, -1] = luma[:, -1] - luma[:, -2]
    dy[1:-1, :] = 0.5 * (luma[2:, :] - luma[:-2, :]); dy[0, :] = luma[1, :] - luma[0, :]; dy[-1, :] = luma[-1, :] - luma[-2, :]
    magnitude = np.hypot(dx, dy); count = max(1, math.ceil(magnitude.size * 0.10)); selected = np.argsort(-magnitude.reshape(-1), kind="stable")[:count]
    mask = np.zeros(magnitude.size, dtype=bool); mask[selected] = True
    return mask.reshape(magnitude.shape), count, float(magnitude.reshape(-1)[selected[-1]])


def metrics(candidate, target, mask, normalization_rms):
    candidate_rgb = candidate[..., :3].astype(np.float64); target_rgb = target[..., :3].astype(np.float64); delta = candidate_rgb - target_rgb
    candidate_y = np.maximum(np.tensordot(candidate_rgb, AP1_LUMA, axes=([2], [0])), 0.0); target_y = np.maximum(np.tensordot(target_rgb, AP1_LUMA, axes=([2], [0])), 0.0)
    rmse = float(np.sqrt(np.mean(np.square(delta))))
    return {"linearRmse":rmse,"linearNrmseByEnsembleRms":rmse/normalization_rms,"linearMae":float(np.mean(np.abs(delta))),"linearP95AbsoluteError":float(np.percentile(np.abs(delta),95)),"linearMaxAbsoluteError":float(np.max(np.abs(delta))),"logLuminanceRmse":float(np.sqrt(np.mean(np.square(np.log2(1+candidate_y)-np.log2(1+target_y))))),"edgeLinearRmse":float(np.sqrt(np.mean(np.square(delta[mask]))))}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--experiment-root",type=Path,required=True); parser.add_argument("--d1-root",type=Path,required=True); parser.add_argument("--output",type=Path,required=True); args=parser.parse_args()
    receipt = json.loads((args.experiment_root/"run.receipt.json").read_text(encoding="utf-8")); refs={}; observations=[]
    for item in receipt["runs"]:
        root=args.experiment_root/item["id"]; report=json.loads((root/"render.report.json").read_text(encoding="utf-8")); path=root/report["artifact"]["uri"]; pixels,roster,canonical=read_combined(path); refs[item["id"]]=pixels
        observations.append({"id":item["id"],"seed":report["settings"]["seed"],"seedOffset":report["settings"]["seedOffset"],"renderSeconds":report["renderSeconds"],"artifact":{"uri":str(path.resolve()),"sha256":sha256_file(path),"bytes":path.stat().st_size},"roster":roster,"combinedCanonicalFloat32Sha256":canonical})
    ensemble=np.mean(np.stack([refs[key].astype(np.float64) for key in ("R512-A","R512-B","R512-C")]),axis=0); ensemble_rgb=ensemble[...,:3]; ensemble_rms=float(np.sqrt(np.mean(np.square(ensemble_rgb)))); mask,count,cutoff=edge_mask(ensemble_rgb)
    pairwise=[]
    for left,right in itertools.combinations(("R512-A","R512-B","R512-C"),2):pairwise.append({"left":left,"right":right,"metrics":metrics(refs[left],refs[right],mask,ensemble_rms)})
    for item in observations:item["metricsAgainstEnsembleMean"]=metrics(refs[item["id"]],ensemble,mask,ensemble_rms)
    d1_analysis=json.loads((args.d1_root/"analysis.json").read_text(encoding="utf-8")); d1_report=json.loads((args.d1_root/"render.report.json").read_text(encoding="utf-8")); candidates=[]
    for cell in d1_report["cells"]:
        path=args.d1_root/cell["artifact"]["uri"]; pixels,_,canonical=read_combined(path,allow_noisy=True); candidates.append({"id":cell["id"],"samples":cell["samples"],"denoising":cell["denoising"],"renderSeconds":cell["renderSeconds"],"combinedCanonicalFloat32Sha256":canonical,"metricsAgainstEnsembleMean":metrics(pixels,ensemble,mask,ensemble_rms)})
    d1_ref=next(item for item in d1_analysis["observations"] if item["id"]=="S512_REFERENCE"); a=next(item for item in observations if item["id"]=="R512-A"); same_seed_exact=a["combinedCanonicalFloat32Sha256"]==d1_ref["combinedCanonicalFloat32Sha256"]
    independent_distinct=len({item["combinedCanonicalFloat32Sha256"] for item in observations})==3
    mean_bytes=np.ascontiguousarray(ensemble.astype("<f8")).tobytes(order="C")
    result={"schemaVersion":"bfs.independentReferenceCalibrationAnalysis.v0.1","protocolCommit":receipt["protocolCommit"],"toolFreezeCommit":receipt["toolFreezeCommit"],"runtime":{"python":platform.python_version(),"openImageIO":oiio.VERSION_STRING,"numpy":np.__version__},"receiptSha256":sha256_file(args.experiment_root/"run.receipt.json"),"d1AnalysisSha256":sha256_file(args.d1_root/"analysis.json"),"sameSeedReproduction":{"d1Id":"S512_REFERENCE","d2Id":"R512-A","exact":same_seed_exact,"d1Hash":d1_ref["combinedCanonicalFloat32Sha256"],"d2Hash":a["combinedCanonicalFloat32Sha256"]},"independentSeedHashesDistinct":independent_distinct,"ensembleMean":{"dtype":"float64-le","shape":list(ensemble.shape),"sha256":hashlib.sha256(mean_bytes).hexdigest(),"rgbRms":ensemble_rms},"edgeMask":{"selection":"stable exact top-k","fraction":0.10,"pixelCount":count,"gradientCutoff":cutoff},"references":observations,"pairwise":pairwise,"d1CandidatesAgainstEnsemble":candidates,"cleanup":receipt["cleanup"],"usableForFormalDesign":same_seed_exact and independent_distinct and receipt["cleanup"]["experimentContainersRunningAfter"]==0}
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(f"BFS_B48_D2_ANALYSIS_OK usable={result['usableForFormalDesign']} sameSeedExact={same_seed_exact} independentDistinct={independent_distinct}",flush=True)
    for item in pairwise: print(f"BFS_B48_D2_PAIR {item['left']}:{item['right']} nrmse={item['metrics']['linearNrmseByEnsembleRms']:.9f} logY={item['metrics']['logLuminanceRmse']:.9f} edge={item['metrics']['edgeLinearRmse']:.9f}",flush=True)


if __name__=="__main__":main()
