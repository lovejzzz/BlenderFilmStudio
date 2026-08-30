# Film Engine public fork C1：三路径兼容发布 PASS

状态：**PASS**

日期：2026-08-30

授权合同：`specs/ai-native-studio-repository-publication-c1-execution.v0.4.json`

证据根：`experiments/ai-native-studio-post-f0/repository-publication-c1-2026-08-30-mac-m2max-attempt-01`

公开仓库：<https://github.com/lovejzzz/film-engine>

## 1. 结论

owner授权的C1已按exact边界完成。现有`lovejzzz/film-engine`仍是public `blender/blender` fork，未删除、重建或重命名。远端`main`由GitHub generated OID `08bed5b5b42ec017e8dcc87b76f6c373c322b086`经一次精确`--force-with-lease`更新为：

```text
4061e12bd45a2bec83e68d0cf49abbf56d4738f6
```

新commit tree为`5f0cb3eb964f4d747ca3a5c9fcb8545cee6773ba`，唯一parent exact为`fa1b578bb421bbc82b3106b7d4223e11e65fae1d`。独立auditor不import runner，59/59检查全部PASS。

## 2. Exact three-path surface

相对parent只变化：

1. `.gitattributes`；
2. `release/darwin/Blender.app/Contents/Resources/blender_icon_legacy.icns`；
3. `release/datafiles/splash.png`。

`.gitattributes`只在原内容末尾追加两条冻结override。icon ordinary blob为`497c866c67f1dd5f2ba08ed2ae4c93d5ad1e7256`，SHA-256仍为`be94271b6759adbe6fa7dc96dbce6cf68a371f0212757a4d28667c535586a468`，2,135,147 bytes。splash ordinary blob为`9af8454bd891d834f10e2ebf072186e567fc7b3e`，SHA-256仍为`5d8b343b125aca7161dcf4e753b9fb39498c182667aa522252dcd9a9f56982cf`，565,997 bytes。

fresh local与fresh GitHub remote `GIT_LFS_SKIP_SMUDGE=1` clones均直接materialize两份完整binary；两个路径的`filter`、`diff`、`merge`和`text`都为`unset`。

## 3. 远端写入边界

执行器只发起一次Git push，命令绑定：

```text
--force-with-lease=refs/heads/main:08bed5b5b42ec017e8dcc87b76f6c373c322b086
```

push从fresh bare副本执行并显式绑定empty hooks目录。结果计数为repository create / LFS upload / Git push attempt / Git ref update / other ref / tag / release / Phase B = `0 / 0 / 1 / 1 / 0 / 0 / 0 / 0`。远端最终仍只有`main`，0 tag、0 PR、0 release。

retained shallow F0 checkout和accepted full-history readiness source都未修改；先前GitHub LFS policy failure及其33/33 audit继续保留。

## 4. Receipts

| Receipt | Self hash |
|---|---|
| preflight | `1032a3b892ec34a63763b879d46f30415f786db3844f90617a8d15d58a8bc4c0` |
| construction | `5f1e49a53abac515250746fdce70d6ba8ac3de32760d85b1b58803ee10bc54bd` |
| local verification | `08f032e942f81cd29a4c88a3865dd69a757c7bec59fa4297f2730068cfdbd189` |
| lease recheck | `2c111976780bb2be2f35d2ecc764c2429167ae30132a6b27c19962fb4b6c3f8e` |
| main update | `8601c496f1f29b26c037b6659ed62dcce77bee5507973703cbc477786d1e29a8` |
| remote verification | `f9de98f2466f806a4fe1b72cc3327f40126a75f9023752bc7bd97e257022e08e` |
| runner verdict | `f20c18aaacaae8835ea7ed7c18cade90c2d31757f54a84f3a92c3e28b827b0b0` |
| independent audit | `71d6e9d581c65fd56242385b18e4aa9c3287d771d583931662571154c6b41cd6` |

## 5. Remaining boundary

C1只关闭source publication compatibility。它不授权release、Developer ID signing、notarization、DMG distribution或任何Phase B source mutation。下一次source/product动作必须来自新的明确授权和版本化protocol；一般“继续”不能跨越Phase B gate。
