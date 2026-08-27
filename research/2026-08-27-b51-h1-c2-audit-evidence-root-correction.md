# B51-H1-C2：审计证据根与输出目录解耦

日期：2026-08-27  
范围：独立重放路径解析，不重新渲染

首次独立审计把重放结果写入临时目录，这是正确行为；但分析器把 `output.parent` 同时当作 EXR 证据根，因此错误地去临时目录寻找 `TW_CPU_R1/artifacts/production.exr`。

失败记录保留于：

- `experiments/native-metal-production-holdout-v0-1/audit.initial-failure.json`

唯一允许的修正是：EXR 证据根固定为不可变 receipt 文件的父目录，结果输出路径仍可位于任意临时目录。EXR、receipt、指标、阈值、攻击、base failure 和负 verdict 均不改变。
