# B35 delayed-disclosure package result

日期：2026-08-26（America/New_York）

工程状态：**`PRIVATE_PACKAGE_VALIDATED_COLLECTION_NOT_OPEN`**

人类证据：**`HUMAN_REVIEW_PENDING` · 0/18**

这两个状态不能合并。B35 证明一套新的、延迟披露的人类审片载体可以由真实 Blender 构建并通过工程审计；它没有证明 Q8、NATURAL 或无差异，也没有证明电影感。

## 新 realization

预注册 commit `eff96fa` 在任何 B35 工具或输出前冻结 spec SHA-256 `2a6af8e5d084b29dd51fc69acb3a96223cae477c85c815ea48c2667781ebf83f`。每个 source process 都要求 active camera 原 lens 为 50.0 mm，再只在内存中统一改为 52.0 mm；源 `.blend` 不保存且运行后保持字节不变。

真实 Blender 5.2 执行完成：

- 13/13 唯一 source PID；
- 1,872/1,872 fresh float32 EXR renders；
- 432 scene-linear composite EXR；
- 432 ACES 2 display PNG；
- 3 条 lossless carrier，合计 432/432 decoded RGB frame pixel exact；
- B35 的 432/432 display frame 与 3/3 carrier 均不同于 B34 对应 identity。

16/16 frozen attacks 通过，其中包括向模拟 public surface 注入一个 sensitive registry value；scanner 必须且实际返回 `PUBLIC_STATE_LEAK_AUDIT_FAIL`。干净 public state 对 3,226 个敏感身份得到 0 match、0 tracked private path。

## 独立复核

独立 Node audit 重新读取并绑定 1,872 source EXR、432 composites、432 display PNG、432 decoded frames 与 18 个 session，结果为 `PRIVATE_PACKAGE_AUDIT_PASS`。

两个独立 `--factory-startup` Blender 5.2 进程分别重新计算全部 432 个 scene-linear float composite；两次最大绝对误差均为 `0.0`，changed float values 均为 `0`，两份 audit report 字节完全相同。

这些是工程 measured facts，不是人类视觉判断。

## 为什么公开内容很少

B34 已证明公开 method-labelled carrier SHA 与 observer CLIP SHA 可以 join 解盲。因此 B35 在 collection close 前不提交任何 method-labelled output/carrier/decoded/display identity、mapping、session binding 或 response。

本轮只公开两个 salted commitment：

- private package commitment：`5ab10b6e97fa1fda1480b48582d7b723cce651aa8bf34f8d5e2e20365c8b5001`；
- sensitive registry commitment：`c1ce83b0a168327b01738a3cd8db1074952cc0bd3804f43fec690ae85b9ea2e9`。

它们绑定私有证据，但不能直接连接到某个方法或 CLIP。公开 artifact 自身与 3,226 个 registry values 的匹配数为 0。

## 当前边界

`COLLECTION_NOT_OPEN` 是主动门禁，不是缺少工程能力。正式采集还需要：把 public commitment 与页面提交部署后，对最终公开 commit 再执行 same-state leak audit；再做不计入样本的界面 pilot；然后才能逐人分发私有 session。每一份 response 被接受前都必须重新通过同一公开面审计。

人类 count 仍是 0。participant blinding 不等于独立 operator double-blinding；远程显示器不统一；motion blur、4K 投影、跨场景/机器、表演、叙事、photorealism 与整体电影感均不在声明内。

## 公开证据

- `experiments/human-quadrature-review-v0-2/precollection-commitment.json`
- `specs/human-quadrature-review-spec.v0.2.json`
- `research/2026-08-26-b35-delayed-disclosure-human-review-protocol.md`

完整 method-labelled evidence 只存在 ignored private work，直到 collection close 或不可恢复的 abort 被先行冻结。
