"""Analyze B49-D1 resolution/time/RSS/EXR scaling."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


EXPECTED=["BFS_MASTER.Combined","BFS_MASTER.Depth","BFS_MASTER.Normal","BFS_MASTER.Vector","BFS_MASTER.CryptoObject00","BFS_MASTER.CryptoObject01","BFS_MASTER.CryptoObject02"]
BASELINE_HASH="4e255e4fa7fdfac9c61d5cfa72d86525714203b7e0b9f1b8be9d99bd26d3dddd"


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):digest.update(chunk)
    return digest.hexdigest()


def inspect(path,width,height):
    first=oiio.ImageBuf(str(path),0,0);roster=[];pixels=None;channels=None
    for index in range(first.nsubimages):
        image=oiio.ImageBuf(str(path),index,0);spec=image.spec();name=str(spec.getattribute("oiio:subimagename") or "");roster.append(name)
        if name.endswith(".Combined"):pixels=np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT),dtype="<f4"));channels=list(spec.channelnames)
    if roster!=EXPECTED or pixels is None or pixels.shape!=(height,width,4) or not np.isfinite(pixels).all():raise RuntimeError(f"invalid B49 EXR: {path}")
    metadata={"name":"Combined","shape":list(pixels.shape),"channels":channels,"dtype":"float32-le","order":"C"};header=json.dumps(metadata,sort_keys=True,separators=(",",":")).encode()+b"\n";return roster,hashlib.sha256(header+pixels.tobytes()).hexdigest()


def exponent(metric_ratio,pixel_ratio):return math.log(metric_ratio)/math.log(pixel_ratio)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--experiment-root",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args();receipt=json.loads((args.experiment_root/"run.receipt.json").read_text());observations=[]
    for run in receipt["runs"]:
        report=run["report"];path=args.experiment_root/run["id"]/report["artifact"]["uri"];roster,canonical=inspect(path,run["width"],run["height"]);observations.append({"id":run["id"],"resolution":[run["width"],run["height"]],"pixelCount":run["width"]*run["height"],"renderSeconds":report["renderSeconds"],"saveSeconds":report["saveSeconds"],"freshContainerWallSeconds":run["elapsedMs"]/1000,"peakSelfRssKiB":report["peakSelfRssKiB"],"artifact":{"uri":str(path.resolve()),"sha256":sha256_file(path),"bytes":path.stat().st_size},"roster":roster,"combinedCanonicalFloat32Sha256":canonical})
    base=observations[0]
    for item in observations:
        pixel_ratio=item["pixelCount"]/base["pixelCount"];item["ratiosToR1"]={"pixels":pixel_ratio,"renderSeconds":item["renderSeconds"]/base["renderSeconds"],"freshContainerWallSeconds":item["freshContainerWallSeconds"]/base["freshContainerWallSeconds"],"peakSelfRssKiB":item["peakSelfRssKiB"]/base["peakSelfRssKiB"],"exrBytes":item["artifact"]["bytes"]/base["artifact"]["bytes"]};item["effectiveExponentsToR1"]={} if pixel_ratio==1 else {name:exponent(item["ratiosToR1"][name],pixel_ratio) for name in ("renderSeconds","freshContainerWallSeconds","peakSelfRssKiB","exrBytes")}
    result={"schemaVersion":"bfs.resolutionScalingDerivationAnalysis.v0.1","protocolCommit":receipt["protocolCommit"],"toolFreezeCommit":receipt["toolFreezeCommit"],"runtime":{"python":platform.python_version(),"openImageIO":oiio.VERSION_STRING,"numpy":np.__version__},"receiptSha256":sha256_file(args.experiment_root/"run.receipt.json"),"b48Baseline":{"expectedCombinedCanonicalFloat32Sha256":BASELINE_HASH,"observedCombinedCanonicalFloat32Sha256":observations[0]["combinedCanonicalFloat32Sha256"],"exact":observations[0]["combinedCanonicalFloat32Sha256"]==BASELINE_HASH},"observations":observations,"cleanup":receipt["cleanup"],"usableForFormalDesign":observations[0]["combinedCanonicalFloat32Sha256"]==BASELINE_HASH and receipt["cleanup"]["experimentContainersRunningAfter"]==0}
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(f"BFS_B49_D1_ANALYSIS_OK usable={result['usableForFormalDesign']} baselineExact={result['b48Baseline']['exact']}",flush=True)
    for item in observations:print(f"BFS_B49_D1_SCALE {item['id']} pixels={item['pixelCount']} render={item['renderSeconds']:.6f}s rssKiB={item['peakSelfRssKiB']} bytes={item['artifact']['bytes']}",flush=True)


if __name__=="__main__":main()
