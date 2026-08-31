# PB.1 C3 attempt-04 retained runtime-isolation failure

Date: 2026-08-31

Status: `FAIL` retained; independent failure audit `PASS` 39/39

Attempt-04 passed formal preflight, 10/10 negative controls, engine and dependency LFS materialization, full history/metric/license checks, and one clean native arm64 build. The build completed in 602.91 seconds with 2,056,978,432-byte peak RSS; the resulting 182,300,520-byte binary SHA-256 is `4d7f1744aca10f4edba527af6dd6a2fa12e78725d8c6887b90dbbce5f2b78a59`. All ten build checks passed.

Both zero-render product starts returned the expected `Film Studio Engine F0 5.2.1 LTS`, build hash `4061e12bd45a`, binary path and bundle identity. The run failed only because macOS application-support resolution ignored the process `HOME` override: all four product paths resolved under the real `/Users/mengyingli/Library/Application Support/FilmStudioEngineF0/5.2`, while the fresh isolated root remained absent. The official Blender configuration digest was unchanged.

The product wrote `config/userpref.blend` in that real product namespace (179,901 bytes, SHA-256 `5c635b481c675f3a4fc4a95ae851ab8a68442ed690d6014597477df9aa320dc1`). This observed side effect is retained and is not deleted or rewritten.

Evidence root: `experiments/ai-native-studio-phase-b/PB.1-2026-08-31-mac-m2max-attempt-04`. Build/runtime/failure/verdict receipt hashes are `fb8bac48…`, `f5ca6f7a…`, `4b1d47b4…`, `6c44c24a…`; independent failure audit receipt hash is `b1f44e80d548979bdd07bd5fc273cfa8421997cbbd0eec7b64cf30b4e8928b29`.

Attempt-04 must remain immutable. A fresh C4 recovery may reuse its accepted build and perform at most two additional zero-render starts with the four `BLENDER_USER_*` paths explicitly bound to fresh isolated directories. It does not require or permit another clone, LFS materialization, dependency clone or native build.
