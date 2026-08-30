# Film Engine public fork C1：GitHub 新 LFS 对象策略阻塞

状态：**BLOCKED_AWAITING_SUPERSEDING_AUTHORIZATION**

日期：2026-08-30

父授权：`research/2026-08-30-film-engine-public-fork-execution-authorization-v0.2.zh-CN.md`

失败证据：`experiments/ai-native-studio-post-f0/repository-publication-2026-08-30-mac-m2max-attempt-01`

机器修正：`specs/ai-native-studio-repository-publication-c1.v0.3.json`

## 1. 保留结果

v0.2执行器通过实时preflight并只执行授权动作。GitHub成功创建：

- repository：`lovejzzz/film-engine`；
- kind：public fork；
- parent：`blender/blender`；
- GitHub repository id：`1351574987`；
- generated `main`：`08bed5b5b42ec017e8dcc87b76f6c373c322b086`；
- branch：仅`main`；
- PR / release：0 / 0。

LFS dry-run exact只列出两个allowlisted OID。正式上传在0/2、0 bytes时被GitHub服务端拒绝：

```text
batch response: @lovejzzz can not upload new objects to public fork lovejzzz/film-engine
```

runner立即停止，没有执行lease recheck或Git ref push。最终副作用为repository create / LFS upload / Git ref update / release / Phase B = `1 / 0 / 0 / 0 / 0`。没有删除、重建或重命名fork。独立failure auditor重算五份receipt、live repository与source状态，33/33 PASS；failure/audit receipt hashes分别为`31cb9ed7db300281d0f76d6a78bd726b435265a7e8eb6e2a3aac2a4438720d7f`与`eb8e9ec13eef1b767f9315ed4c0aee195f14e07c41f65ddc2320ff75e3fe7c0f`。

## 2. 根因

这是server-side policy failure，不是quota、文件大小、认证或lease failure：

- 两个文件只有2,135,147与565,997 bytes，远低于100 MiB ordinary Git blob ceiling和GitHub LFS per-file ceiling；
- active login与repo owner exact为`lovejzzz`；
- dry-run识别本地两个对象，正式batch request才被public-fork rule拒绝；
- Blender source checkout的LFS endpoint来自official remote `https://projects.blender.org/blender/blender.git/info/lfs`；GitHub `blender/blender`是mirror，无法让本fork向GitHub LFS storage播种这两个新品牌OID。

Git LFS官方仓库已有同一GitHub错误的保留记录，并把它描述为防滥用服务端规则：<https://github.com/git-lfs/git-lfs/issues/1449>。GitHub billing文档说明fork使用量与repository owner/parent相关，但费用接受不能绕过server policy：<https://docs.github.com/en/billing/concepts/product-billing/git-lfs>。

## 3. 不允许的“修复”

当前授权不允许：

- 在缺失两个LFS data objects时仍把`fa1b…` pointer tree推到`main`；
- 重试同一被服务端禁止的上传；
- 删除、重建或重命名现有fork；
- 创建standalone repository或新的LFS host；
- 上传全部6,671个LFS对象；
- 改写历史、无lease force、修改其他ref/tag；
- 开始Phase B、创建release、签名、公证或分发DMG。

## 4. 推荐的最小C1路线（尚未授权）

推荐保留当前public fork和完整上游network，只新增一个**publication compatibility commit**，parent必须exact为`fa1b578bb421bbc82b3106b7d4223e11e65fae1d`。该commit只允许三条path变化：

1. `.gitattributes`在现有通配LFS规则后追加两个exact-path override；
2. `release/darwin/Blender.app/Contents/Resources/blender_icon_legacy.icns`从LFS pointer blob变为相同内容的ordinary Git blob；
3. `release/datafiles/splash.png`从LFS pointer blob变为相同内容的ordinary Git blob。

冻结override：

```gitattributes
release/darwin/Blender.app/Contents/Resources/blender_icon_legacy.icns -filter -diff -merge -text
release/datafiles/splash.png -filter -diff -merge -text
```

内容不变门：

| Path | Content SHA-256 | Bytes | Proposed ordinary Git blob |
|---|---|---:|---|
| icon | `be94271b6759adbe6fa7dc96dbce6cf68a371f0212757a4d28667c535586a468` | 2,135,147 | `497c866c67f1dd5f2ba08ed2ae4c93d5ad1e7256` |
| splash | `5d8b343b125aca7161dcf4e753b9fb39498c182667aa522252dcd9a9f56982cf` | 565,997 | `9af8454bd891d834f10e2ebf072186e567fc7b3e` |

C1必须在新的外部worktree实施，不修改retained F0 checkout；commit前要求exact 3 paths、0 code-line change、两份binary SHA/bytes unchanged、fresh `GIT_LFS_SKIP_SMUDGE=1` clone仍直接取得两个完整文件。最终只允许一次`--force-with-lease=refs/heads/main:08bed5b5…`更新现有fork `main`到新C1 commit；仍不允许LFS upload、release或Phase B。

这条路线会使最终`main`不再exact等于`fa1b…`，而是以`fa1b…`为唯一parent的新commit，因此必须由owner重新明确授权，不能从v0.2推断。

## 5. 其他路线

- 等待/联系GitHub Support请求解除public-fork LFS限制：不改source，但外部support message尚未授权，结果和时延未知。
- standalone repository + full LFS transfer：仍需要新的repository topology、rename/delete选择、全部LFS transfer和计费授权；不是当前动作，继续BLOCKED。

在owner给出新授权前，现有fork保持GitHub生成的upstream `main`，不再写入。
