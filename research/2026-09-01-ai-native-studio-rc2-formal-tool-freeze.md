# RC2 formal tool freeze

Date: 2026-09-01

RC2 formal tools are frozen before either formal root exists. The frozen
product commit is `636f42f28f781f3e858fd5b6bf641910a549c91b`, with exactly two
changed paths and no public push. The machine runner performs one local-only
source clone, one clean native arm64 build and three offline product starts:
PC8/PC9 plus RC1 source compatibility, RC2 build/save/render, and RC2 reopen.

The machine contract is
`specs/ai-native-studio-rc2-physical-light-formal-tool-freeze.v0.2.json` at
freeze hash `42b483217e24bcd27d2c8057ba1fb01db3c6144a7f29182d7924022dd2e0910e`.
It binds the preregistration, fixture, three formal tools, two product files,
accepted 165/160 GiB resource admission and all mutation/process ceilings.

No formal work/evidence root, engine remote write, release, binary
distribution, signing or notarization exists at freeze.
