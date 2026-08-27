# B51-D4-C3 · deterministic `capDate` correction protocol

Status: preregistered before correction tooling or output.

## Falsifiable question

Is OpenImageIO's wall-clock `capDate` injection the complete cause of D4's container non-determinism, such that explicitly deriving OIIO `DateTime` from the frozen Metal beauty source makes all four split-backend multipart EXRs and the complete evidence bundle byte-exact without changing any selected float array?

## Bound failure

C3 binds the original D4 spec, invalid receipt, invalid result, failed audit and the exact parent tool blobs in `specs/native-split-backend-assembly-capdate-correction.v0.1.json`, SHA-256 `911665b8a5e6660440e5cb6c0d8cf68ef17191c2d40187cc2f698a13198c9ec9`. The invalid TABLETOP pair differed at exactly seven bytes. Each byte occupied the seconds digit of the auto-generated OpenEXR `capDate`, once per subimage. The source pixels, selected output pixels, roster and provenance all passed.

## Only allowed correction

For each pair, the corrected writer must:

1. read `Date` only from the frozen Metal `BFS_MASTER.Combined` source spec;
2. require exact `YYYY/MM/DD HH:MM:SS` syntax and the preregistered value for that pair;
3. replace only the two date slashes with colons;
4. set the resulting OIIO `DateTime` on every one of the seven output specs before opening the OpenEXR writer;
5. reopen every part and require the same `DateTime` value;
6. persist source, derived and observed values in the evidence.

OpenImageIO's OpenEXR writer source states that it generates current local `DateTime` only when the client does not supply one. OIIO maps `DateTime` to OpenEXR `capDate`. The correction therefore supplies source-derived capture metadata rather than deleting metadata or inventing a wall-clock constant.

## Frozen remainder

The four source EXRs, CPU/Metal role checks, pair identities, pass routing, seven-part roster, geometry, common metadata, Cryptomatte manifest, provenance, float exactness, finite checks, two replicates per pair, container byte identity, 100 GiB reserve, 64 MiB projected write, original fifteen attacks and independent byte-exact replay remain unchanged. Four new correction attacks cover parent identity, source capture date, output value and seven-subimage totality.

No Blender process, render, download, model call or source mutation is allowed. Output goes only to `experiments/native-split-backend-assembly-capdate-correction-v0-1`. A failure is retained and does not advance B51-H2.

## Promotion boundary

C3 is usable only if:

- all original base gates pass;
- all `15 + 4` attacks reach their intended failure reason;
- both within-run merge pairs are byte-exact;
- independent replay reproduces receipt, result and all four EXRs byte-for-byte;
- corrected tool blobs match the receipt's frozen Git commit.

Passing would establish deterministic assembly for these two known H1 pairs only. It would unlock—not answer—the unseen B51-H2 split-backend holdout.
