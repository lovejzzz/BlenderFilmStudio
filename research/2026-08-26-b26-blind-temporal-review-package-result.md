# B26 blinded temporal review package result

Date executed: 2026-08-26

Package status: **`CARRIER_AND_INTERFACE_READY`**

Package validity: **true** (`20/20` frozen negative cases passed)

Human review status: **PENDING / 0 responses**

## Carrier result

The formal runner independently encoded A, B and C as lossless VP9 Profile 1 WebM, `gbrp`, 960×540, 24 fps, six seconds and no audio with the frozen FFmpeg 8.1.2 binary.

- A: 27,496,119 bytes, SHA-256 `0fc70ebc76bec94c810fde72f94f4e2ff659fe04b565183d0bc98b70bfbe077b`;
- B: 27,510,630 bytes, SHA-256 `5d21be2f2b6a8a26c549e0069d1d0ca39dbe54a2c43a90aaeb04577978e8688c`;
- C: 27,492,939 bytes, SHA-256 `538ebb5896e81dc91d7a7df25594376f6486a3ce4c59572511bc2bf8243b95c1`.

Every carrier was decoded back to 144 RGB PNG frames. All three passed 144/144 exact RGB frames, maximum error 0 and zero changed RGB pixels. Every source alpha sample was exactly opaque before alpha omission. Total carrier payload is 82,499,688 bytes.

## Blinding and package result

The runner created 18 observer sessions. Each of the six A/B/C order permutations appears exactly three times. Observer-visible files are only `CLIP-01.webm`, `CLIP-02.webm`, `CLIP-03.webm` plus `index.html`; the sealed source mapping remains under the git-ignored local work directory.

The overall salted mapping commitment is:

`540cc4c76193fc460945968e6919e5684d8a45fee58c5f8dcbcdfdee15a4379b`.

All session clip files are hard links to the three verified carriers rather than 54 physical copies. Mapping commitments and carrier/HTML hashes are public; the mapping itself is not published before response lock.

## Real browser interface check

OBS-01 was served locally and inspected in the Codex in-app browser:

- all three VP9 videos reached ready state 4;
- all reported duration 6 seconds and 960×540 dimensions;
- native controls were absent;
- no `sourceLabel`, `underlyingLabel` or `permutation` token appeared in the observer HTML;
- one complete automated interface playback advanced the counter from 0/2 to 1/2 while the rating remained disabled, then the page was reloaded without creating a response.

This check validates interface behavior only. It is not a human session and does not count as a pilot response.

## Boundary

No human watched and rated the accepted package during this experiment. Formal status therefore remains `PENDING`, with formal response count 0 and pilot response count 0. The project owner/developer may complete OBS-01 only as `INTERFACE_PILOT_ONLY`; at least 15 valid independent observers are required for anything beyond informal description, and the balanced production target remains 18.
