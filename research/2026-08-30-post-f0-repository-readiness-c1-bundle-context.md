# Repository Readiness C1：bundle prerequisite context correction

状态：**在 attempt-02 tool mutation 前预注册**

日期：2026-08-30

父协议：`research/2026-08-30-post-f0-repository-readiness-protocol-v0.1.zh-CN.md`

父机器合同：`specs/ai-native-studio-repository-readiness.v0.1.json`

修正合同：`specs/ai-native-studio-repository-readiness.v0.2.json`

## 1. Retained attempt-01

正式 attempt-01 在 tool freeze commit `6b15e68f6c791a982670fb3cad32d72898fb8f6b` 上运行。RR.1–RR.3 全部通过，RR.4 从 exact `https://github.com/blender/blender.git` 完成一次 read-only bare mirror acquisition：

- mirror 是 non-shallow；
- 2,244,857 objects in one 1.39 GiB pack；
- 含 baseline `fbe6228777e7d9afefcd61a413844e790ae75db7` 与 target `9e2066aef7ef7e20c142ad7bd3303138a4304c93`；
- origin exact，431 refs、273 tags；
- 没有 GitHub repository create、external push、LFS upload 或 local destination init。

source inventory为PASS，receipt hash `c0d4b4dbfa5df4325dfc68fa0243d6dbc2068f7901d5e1bd926c9cf319e9ed90`。它确认16 paths / 909 lines / 4 commits、6,671 LFS paths / 815,089,197 bytes、2个fork-owned LFS branding objects、19个license/notice paths、0 fork-owned secret findings。

随后生成的16 KiB F0 bundle SHA-256为`8018e8b4f1f8f5320aae450910690ae6fb3a91688dcb6a54df5fa35983b3c1c6`。bundle要求两个prerequisites：`fbe62287…`与`9e2066ae…`。

runner错误地在research repository context执行：

`git bundle verify <bundle>`

research repository当然不含两个Blender commits，因此返回“Repository lacks these prerequisite commits”。同一个未修改bundle在retained full mirror context执行：

`git -C <retained-full-mirror> bundle verify <bundle>`

立即报告`is okay`。所以这是`BUNDLE_VERIFY_REPOSITORY_CONTEXT` harness failure，不是source、bundle或full-history failure。

attempt-01永久保留为FAIL：

- failure file SHA-256：`dbb26a4fa754d299550810ad0afcb9a20844c5a68102220802904f9122412c19`
- failure receipt hash：`3d88f56a63e6731b3ab03b71733fd816d8c5237c9c05540160931bc4bee0ddbc`
- failure code：`F0_BUNDLE_VERIFY_FAILED`
- local destination：ABSENT
- external repository creates / pushes / LFS uploads / Phase B mutations：`0 / 0 / 0 / 0`

## 2. 唯一允许的 correction

C1只允许：

1. 把正式spec切到v0.2和fresh attempt-02 roots；
2. 绑定attempt-01 failure与retained mirror/bundle identity；
3. 通过本地`git clone --mirror --local`从retained full mirror建立attempt-02工作mirror，禁止第二次network clone；
4. 在attempt-02工作mirror context执行bundle verify；
5. independent auditor同时验证attempt-01 retained binding、attempt-02 local reuse、0 second external mirror clone。

不允许改变source HEAD/tree、候选owner/slug、public-fork建议、private-mirror BLOCKED状态、8项negative controls、license/secret/blob/LFS门、5 GiB / 8 MiB ceilings或任何授权flag。

## 3. Fresh roots

- evidence：`experiments/ai-native-studio-post-f0/repository-readiness-2026-08-30-mac-m2max-attempt-02`
- external：`/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/repository-readiness-attempt-02`
- retained input mirror：attempt-01 `blender-github-full-mirror.git`，只读身份输入；
- attempt-02 work mirror：attempt-02 `blender-github-full-mirror.git`；
- attempt-02 local destination：attempt-02 `film-studio-engine-local.git`。

attempt-01任何文件、ref或object都不得修改。attempt-02只能从fresh roots开始。

## 4. Claim ceiling

若C1通过，结论仍只可能是public GitHub fork路线`READY_FOR_EXPLICIT_AUTHORIZATION`；不会创建fork、不会首次external push，也不会把private standalone LFS路线升级为ready。
