# B14 receipt-bound review dailies result

Executed: 2026-08-26 against real Blender 5.2.0 LTS build `fbe6228777e7`.

Status: **FORMAL AUTOMATION TRUE / HUMAN REVIEW PENDING**

## Result

The exact B02-A CompileReceipt produced a complete review-proxy sequence and playable video:

- frames: 144/144, names `frame-0001.png` through `frame-0144.png`, no gaps or extras;
- render: 28.324786 seconds total, 0.196700 seconds/frame mean;
- local PNG sequence: 83,216,547 bytes;
- sequence hash: `a52903fc327139ae41ed08f2d257d704b7977e9fda060138b106ceb56dbd56e4`;
- video: 438,567 bytes, SHA-256 `e9f52ad3dc497fbb2e6074c2f79df2fa0c365235c5713a9f29e1ead927b340b8`;
- ffprobe: H.264, yuv420p, 960×540, 24/1 fps, 144 declared and decoded frames, 6.000 seconds, zero audio streams;
- camera/timeline identity before and after rendering: exact JSON equality;
- positive evidence verifier: pass;
- pre-registered attacks: 10/10 rejected with their intended stable reason.

The machine-readable result is `experiments/review-dailies-v0-1/results.json`. The evidence graph, render report and 144-entry sequence manifest are in `experiments/review-dailies-v0-1/evidence/`.

## First implementation defect preserved

Inspection after the first 144-frame run found a tautological in-Blender OCIO availability check: the config cache ID was compared with itself. The outer verifier already checked the exact OCIO SHA, so the formal result was not accepting the wrong bytes, but the Blender-local assertion had no evidence value. The script was corrected to compare the loaded OCIO name with the receipt-verified BuildPlan, and the complete formal sequence was rerun.

The pre-correction run measured 27.119043 seconds and produced sequence hash `4584715f31efcde8c8e88d23d29b7b6d97088707bdea067a320b99360544f014` and video hash `1cbecb1dc1d446daaf599b75cff10fb4a34879a99c7f098bcf8e3eeba6f8780c`. A corrected run then produced sequence `b598e383…313188`, but its evidence command retained an absolute local repository path. Promotion stopped again; the runner now publishes `<REPO>/…` placeholders and the final sequence was regenerated. Because tool identity changed between promoted candidates, these runs are not a controlled determinism test; they motivate a separately pre-registered same-source A/B proxy-pixel experiment.

## Cost interpretation

The mean of the six published B02 4K/512-sample Cycles measurements is 315.646811 seconds/frame. Extrapolating that measured simple-scene rate to 144 frames gives 45,453 seconds, or 12.63 serial hours. B14's Eevee proxy is about 1,605× faster, but it changes engine, resolution, samples, output type and motion-blur policy. This is a dailies-versus-master operational comparison, not an equal-quality cost comparison.

## Non-claims

- The proxy does not satisfy the 4K Cycles master contract.
- Complete frames and a valid container do not prove photorealism, cinematic quality, good composition, acting or temporal perceptual stability.
- H.264 is lossy and is not an archival master.
- Same-machine completion does not prove cross-device reproducibility.
- Human review has not passed; no synthetic review response was created.
- The full 83.2 MB PNG source sequence is not tracked. Public witness frames and hashes do not make discarded bytes reconstructible.

## Next boundary

Run a pre-registered, identical-source A/B review-proxy experiment and compare both PNG container hashes and decoded pixels. Separately collect real human judgments on the complete clip. Neither result can promote the proxy to master quality.
