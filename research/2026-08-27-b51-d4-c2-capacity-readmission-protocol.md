# B51-D4-C2 · capacity re-admission protocol

Status: preregistered after the retained capacity failure and before retry output.

## Retained failure

The C1-corrected runner verified the spec, preregistration ancestry, parent identities and four source EXRs, then created an empty output root and stopped at the frozen disk gate. `df -h` reported only `99 GiB` available; no receipt or merged EXR was written, no Blender process or render occurred, and no scientific result exists.

The immutable failure record is `experiments/native-split-backend-assembly-derivation-capacity-failure-v0-1/failure.json`, SHA-256 `b6b4ebe97d7558150e489200d88ba436fddec1bbd2f2e34af1ae4c559f2a0167`.

## Re-admission action

The user had already explicitly authorized cache cleanup. The exact cache directory `/Users/tianxing/Library/Caches/ms-playwright` measured approximately 1.6 GiB and was removed. It contains redistributable Playwright browser binaries that can be downloaded again; project evidence, source inputs, model weights and personal files were not removed.

After cleanup, `df -k /System/Volumes/Data` reported `108197478400` available bytes. The retry is admitted only if the unmodified runner independently measures:

`availableBytes - 67108864 >= 107374182400`

## Frozen retry

- Tool commit remains `2824e0f9b3207de091436eba3083beda7f5abdd3`.
- Spec, source identities, pass routing, output contract, threshold, attacks, audit and non-claims remain unchanged.
- The existing output root must still be empty when the runner starts.
- No further cleanup is authorized by this protocol.
- Any new failure is retained; it is not repaired inside the run.

This is external-state re-admission, not a change to the scientific or software contract.
