# Film Studio Engine：public fork 创建与首次发布授权请求 v0.1

状态：**REQUESTED_NOT_AUTHORIZED · 0 external mutation**

日期：2026-08-30

父证据：`experiments/ai-native-studio-post-f0/repository-readiness-2026-08-30-mac-m2max-attempt-03`

机器请求：`specs/ai-native-studio-repository-authorization-request.v0.1.json`

## 1. 为什么需要比“first push”更精确

Repository-readiness C2已经证明完整Git graph与exact F0 branch可以在本地安全组合，但真正创建GitHub public fork时还有两个有副作用的细节，不能用一句模糊的“允许首次push”代替：

1. GitHub从`blender/blender`创建fork后会生成自己的默认`main` ref。要让新产品仓库的`main` exact为`fa1b578b…`，必须只在fresh fork、没有owner-authored commit的前提下，用观察到的generated main OID做`--force-with-lease`更新。
2. F0修改了两个Git LFS品牌资产。它们不是upstream已有对象，完整source publication需要向新fork的LFS endpoint上传这两个exact OID；该上传可能计入repository owner的Git LFS storage/bandwidth。

因此这两项必须由owner明示，不能从普通Git ref push暗中推断。

## 2. 唯一请求授权的外部动作

候选仓库：

- owner：`lovejzzz`
- visibility：`public`（GitHub public repository的fork不能独立设成private）
- upstream：`blender/blender`
- requested fork name：`film-studio-engine`
- desired `main`：`fa1b578bb421bbc82b3106b7d4223e11e65fae1d`
- desired tree：`4d761fb73d2b10e051905daedd25cc15da702c27`

授权只覆盖：

1. 调用GitHub fork creation API，请求上述owner/name；
2. 等待并只读验证`fork=true`、`parent.full_name=blender/blender`、visibility public；
3. 读取fresh fork生成的`main` OID，确认仓库没有owner-authored commit；
4. 向该fork LFS endpoint只上传以下两个OID；
5. 用`--force-with-lease=refs/heads/main:<observed-generated-main-oid>`把candidate ref更新为exact F0 `main`；
6. 只读验证GitHub `main`、tree、parents、merge base、LFS下载与license files exact。

不授权删除仓库、修改其他refs、push tags、上传全部6,671个LFS对象、使用`--force`而无lease、创建release、分发DMG、Developer ID/notarization或Phase B mutation。

## 3. Exact fork-owned LFS upload set

| Path | OID SHA-256 | Bytes |
|---|---|---:|
| `release/darwin/Blender.app/Contents/Resources/blender_icon_legacy.icns` | `be94271b6759adbe6fa7dc96dbce6cf68a371f0212757a4d28667c535586a468` | 2,135,147 |
| `release/datafiles/splash.png` | `5d8b343b125aca7161dcf4e753b9fb39498c182667aa522252dcd9a9f56982cf` | 565,997 |

总计：2 objects / 2,701,144 bytes。正式上传前`git lfs push --dry-run --object-id`必须只列出这两个OID；任何第三个对象都停止。

## 4. Fresh-fork lease gate

在修改GitHub `main`前必须同时满足：

- candidate slug在创建前不存在；
- fork由本次已授权动作创建；
- parent exact为`blender/blender`；
- generated `main` OID已写入pre-push receipt；
- fork没有owner-authored commit、PR、release或额外branch；
- push使用显式`--force-with-lease=refs/heads/main:<generated-oid>`；
- source ref仍exact为`fa1b578b…`及tree `4d761fb7…`；
- 两个LFS OID已先上传并可由fork endpoint读取。

任一不满足就停止，不删除或重建仓库来绕过。

## 5. 精确授权句

> 我授权 owner=`lovejzzz` 创建 `blender/blender` 的 public GitHub fork，名称为 `film-studio-engine`；接受只上传上表两个 fork-owned Git LFS 对象（合计 2,701,144 bytes）及其可能产生的 GitHub LFS storage/bandwidth 计费；并且仅在该 fork 为本次新建、无 owner-authored commit 时，使用绑定生成 `main` OID 的 `--force-with-lease` 将 exact `fa1b578bb421bbc82b3106b7d4223e11e65fae1d` 发布为 `main`。签名、公证、unsigned DMG 分发、release 创建和 Phase B mutation 仍未授权。

只有用户明确给出等价授权后才执行。含糊的“继续”“ok”或一般性自动工作授权不满足此门。

## 6. 依据与边界

- GitHub public fork与upstream共享repository network，fork visibility不能独立改变：<https://docs.github.com/en/pull-requests/reference/forks>
- Git LFS storage/bandwidth按repository owner与使用方式计费：<https://docs.github.com/en/billing/concepts/product-billing/git-lfs>
- standalone repository复制LFS需要`fetch --all`与`push --all`，仍不是本请求：<https://docs.github.com/en/repositories/creating-and-managing-repositories/duplicating-a-repository>

这是一份工程授权请求，不是法律或GitHub费用保证。
