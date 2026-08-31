# PB.5 restart-safe job control：PASS

Date: 2026-08-31

Gate: PB.5

Verdict: `PASS`

## 结果

`film-engine` commit `373881e1ee659a962e0015c2dac26f7fa981b1bf` 在三个既有 Python 产品路径中加入 restart-safe render job control。增量为 274 additions / 10 deletions，没有 C/C++、网络权限、unrestricted model Python、shell 或 filesystem authority。一次 clean native arm64 build 成功，binary SHA-256 为 `8b9e680b97015c2a6b71da404df3d4dcd3148dfe63b8f6a3534cc0e12390c592`。

正式 attempt-01 完成冻结的四启动序列：

1. 第一次启动只完成并 fsync PREVIEW，随后以 exit 75 受控中断。
2. 第二次启动验证已有 PREVIEW artifact/receipt，只执行 FINAL；PREVIEW bytes 保持不变。
3. 第三次启动看到 COMPLETE，零 render no-op；两个完成 artifact 均保持不变。
4. 第四次启动以零 render 分别拒绝 stale、forged preview receipt 与 exhausted budget，并运行不导入产品模块的独立 OpenImageIO audit。

总计 1 clean build、4 product starts、2 render calls、0 model calls、0 network calls、0 mouse interactions、0 releases/signing/notarization/distribution。最终 receipt 的 13/13 checks 全为 true，独立审计的 source、receipt、resume、failure、pixel/pass checks 全部通过。

## 关键证据

- Evidence root: `experiments/ai-native-studio-phase-b/PB.5-2026-08-31-mac-m2max-attempt-01`
- Validation receipt self hash: `1baa24ee3f70539bc992f8a7177d5f0a478affe3d68f7b26d65e8dd617079220`
- Independent audit self hash: `a18a32c3b25b4d4f8deceda88784498d51ad291568e0bf4c2f6810c5d35527dd`
- Interruption receipt self hash: `311e672ce6adc21027b5faa4eafc47d30f0a2e736745472c6c645381e1271b39`
- PREVIEW artifact SHA-256: `90d2cf9edca92b6b3d54e78fe8bd7f0f1fe78f06e850563abfd276b2ed3f71f8`
- FINAL artifact SHA-256: `947d2217d2b441a45b5072465166ae9100d62c14ee70a846237367fb56b97d15`
- Cost receipt self hash: `042427f202018f1d368bb3e6d9b56853db6bceecac171b3562354b2ebd7efd33`
- Work / evidence bytes: 10,082 / 4,455,304，均低于冻结上限。

三项 failure reason 分别为 `JOB_EXPIRED`、`PREVIEW_RECEIPT_INVALID` 与 `RENDER_BUDGET_EXHAUSTED`，每项 process renderCalls 均为 0，source hash unchanged，new render artifacts 为 0。

## Retained correction

`specs/ai-native-studio-pb5-render-job-attempt-01.v0.2.json` 在正式运行前被发现：最后绑定 tool-freeze commit 后没有重新计算 `manifestHash`。它已经作为未执行的冻结清单保留。v0.3 仅更新正确的工具绑定、自校验值并明确 cross-bind v0.2；正式 runner 在创建 work root 或启动 Blender 前验证 v0.3 self hash 与三份工具 SHA-256。没有覆盖失败记录，也没有复用 formal root。

## Claim ceiling 与下一 gate

本结果只证明 admitted M2 Max host、冻结 B01 scene、冻结 PREVIEW/FINAL profiles 下的单任务双阶段恢复与三项预注册攻击。它不证明多任务调度、跨主机恢复、生产可用性或公开发行。

PB.6 必须另行预注册 B62 wide / medium / close 三镜头垂直切片；三镜头应共享冻结的非摄影机状态，并保留 frame-288 构图拒绝，不能自动放宽人类质量阈值。
