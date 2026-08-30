# Film Engine：public fork 首次发布执行授权 v0.2

状态：**AUTHORIZED_PENDING_EXECUTION · 0 external mutation at freeze**

日期：2026-08-30

授权观察时间：`2026-08-30T16:37:48Z`

父请求：`research/2026-08-30-film-studio-engine-public-fork-authorization-request-v0.1.zh-CN.md`

父请求 SHA-256：`81f56ef09dacfa11f1767b7a9c3d59c3398151613b7133bd1a9adbcb67070128`

机器授权：`specs/ai-native-studio-repository-authorization-request.v0.2.json`

## 1. 版本化变更

v0.1 请求的候选名称是 `film-studio-engine`。owner 在当前 Codex 任务中给出等价授权时，将名称明确改为 `film-engine`。本文件只版本化这一名称变更和授权状态；source head、tree、两个 LFS OID、lease 条件、计费接受以及所有未授权边界保持不变。v0.1 不回写。

## 2. Owner 原文授权

> 我授权 owner=lovejzzz 创建 blender/blender 的 public GitHub fork，名称为 film-engine；接受只上传机器请求所列两个 fork-owned Git LFS 对象（合计 2,701,144 bytes）及其可能产生的 GitHub LFS storage/bandwidth 计费；并且仅在该 fork 为本次新建、无 owner-authored commit 时，使用绑定生成 main OID 的 --force-with-lease 将 exact fa1b578bb421bbc82b3106b7d4223e11e65fae1d 发布为 main。签名、公证、unsigned DMG 分发、release 创建和 Phase B mutation 仍未授权。

## 3. 唯一获授权的外部动作

- 以当前 active GitHub identity `lovejzzz` 调用 `blender/blender` fork creation API，请求名称 `film-engine`，visibility 保持 `public`；
- 创建前再次确认 `lovejzzz/film-engine` 不存在，且 `lovejzzz` 没有 `blender/blender` fork；
- 请求 `default_branch_only=true`，避免创建未经授权的额外 branch；
- 创建后只读观察 GitHub 生成的 `main` OID，并验证 fork、parent、visibility、branch、PR、release 和 owner-authored commit 门；
- 只上传以下两个 fork-owned LFS OID；
- 只用 `--force-with-lease=refs/heads/main:<observed-generated-main-oid>` 将 exact `fa1b578bb421bbc82b3106b7d4223e11e65fae1d` 发布到 `refs/heads/main`；
- 只读验证最终 remote head/tree/parents/merge-base、两个 LFS 对象、license/notices 与 GitHub metadata。

| Path | OID SHA-256 | Bytes |
|---|---|---:|
| `release/darwin/Blender.app/Contents/Resources/blender_icon_legacy.icns` | `be94271b6759adbe6fa7dc96dbce6cf68a371f0212757a4d28667c535586a468` | 2,135,147 |
| `release/datafiles/splash.png` | `5d8b343b125aca7161dcf4e753b9fb39498c182667aa522252dcd9a9f56982cf` | 565,997 |

总计：2 objects / 2,701,144 bytes。

## 4. 冻结的 pre-mutation 观察

- active GitHub login：`lovejzzz`；
- `lovejzzz/film-engine`：HTTP 404 / absent；
- owner 现有 fork 仅 `lovejzzz/SmallHelper`，parent 为 `obot-platform/nanobot`；没有 `blender/blender` fork；
- local full-history source：non-shallow bare repository，`main=fa1b578b…`，tree `4d761fb7…`，parents exact，162,917 reachable commits，只有 `refs/heads/main`；
- 两个 LFS data object 均已下载；实际 byte size 与 SHA-256 分别 exact；
- repository-readiness 8/8 negative controls 重新通过；
- 初次观察剩余 155 GiB，低于通用 F0 新构建门的 160 GiB。owner 随后授权空间清理；只删除无打开文件、2026-07-20 后未更新的 Coursemapper Chrome device-profile cache `tutor-gbnf-v45-chrome`（22,044,484 KiB），未动 Hugging Face、Codex、Blender 或证据文件。清理后剩余 176 GiB，`F0_HOST_PREFLIGHT_ACCEPTED`；本次仍不执行新 source build。

## 5. 仍未授权

无 lease force、删除或重建 fork、修改其他 branch/tag、上传第三个 LFS OID、创建 release、签名、公证、unsigned DMG 分发、Phase B source mutation，以及任何新 Blender build 均不在本授权内。

如果任一 fresh-fork 或 exact-object 门失败，执行必须停止并保留 failure evidence；不得删库重来。
