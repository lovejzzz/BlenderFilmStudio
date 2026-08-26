# B32 formal protocol · deterministic quadrature cost–quality holdout

日期：2026-08-26（America/New_York）
状态：`PREREGISTERED_BEFORE_FORMAL_TOOLING_OR_OUTPUTS`

## 目的

B32/B32.1 在已暴露的 derivation frames 37、72、103 上看到：Q4 保持 exact A/B 并恢复大量 CENTER 的 edge-reference 误差，Q8 又以约 2× Q4 成本将 mean edge error 降低约 24.2%。本次正式 holdout 检验这条 1× NATURAL、4× Q4、8× Q8 成本—质量曲线能否外推到新 frame。

主协议是 `specs/quadrature-cost-holdout-spec.v0.1.json`，SHA-256 为 `5503bca51c5f6aac1f8f26c86f2714bef83db8de11a85514a8968d0b52c73e64`。本文与 spec 在正式 renderer、analyzer、runner 或输出存在前提交。

## 冻结实验

- 帧：`22, 59, 97, 136`，均未用于 B31/B32 quality derivation/holdout；
- NATURAL32 A/B：2 个新 PID、8 renders；
- NATURAL1024 reference A/B：2 个新 PID、8 renders；
- Q4 A/B：8 个新 PID、32 renders；
- Q8 A/B：16 个新 PID、64 renders；
- 合计 28 个 unique Blender PID、112 次 EXR32 render；
- 场景、Blender build、OCIO、960×540、Eevee、fixed 8 threads、motion blur off 与 dither 0 全部冻结；
- Q4/Q8 只在 scene-linear RGB 中等权合成；
- edge mask 是每帧 dual-reference mean 上 RGB central-difference magnitude top 5%。

## 冻结门槛

Formal result 先分别输出五个 component verdict，再给 overall decision：

1. reference A/B edge RMSE / mean NATURAL32 edge RMSE 每帧 `<= 0.05`；
2. Q4 composite A/B 与 Q8 composite A/B 每帧都必须 float exact；
3. Q4/NATURAL edge ratio 每帧 `<= 1.40`；
4. Q8/NATURAL edge ratio 每帧 `<= 1.10`；
5. Q8/Q4 edge ratio 每帧 `<= 1.0`，且四帧 mean `<= 0.90`。

五项都通过才是 `COST_QUALITY_CURVE_SUPPORT`。任一失败就是 `COST_QUALITY_CURVE_PARTIAL_OR_FAILURE`，并按 spec 的 failure precedence 保留具体原因，不用 overall label 掩盖局部反例。

Render seconds 必须记录，但不设为硬门：固定 component 数已经构成 4/8 次渲染调用的主成本，秒数会受机器负载和启动摊销影响。

## 有效性和攻击

正式 runner 必须从空 evidence/work 目录开始，核对 28 个子进程 PID、每个 report/output hash 与全部 runtime/source identity。分析器必须对 spec、results 和原始 EXR 绑定。至少攻击：改 spec/hash、改帧/点/权重/采样/线程、重复 PID、缺 report/output、改 output hash、改 metric/decision，以及非空 output directory。

正式运行后再用新 factory-startup Blender 重算 analysis；只有 byte-exact 结果才能记为分析可复现。

## 不予声明

即使 overall 通过，也只确认这台机器、这个 Blender build、场景、四个 holdout frame 上的 scene-linear proxy 成本—质量曲线。它不等于肉眼 near-natural、时序稳定、motion blur 正确、电影感或生产可接受，也不证明点集最优。
