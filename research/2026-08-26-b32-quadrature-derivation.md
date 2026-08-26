# B32 derivation · deterministic four-point jitter quadrature

日期：2026-08-26（America/New_York）
状态：`EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`

## 问题

B30 证明单点 CENTER32 strict stable；B31 又确认它在四个 holdout frame 上带来 2.17–2.86× 的 edge-reference RMSE。B32 derivation 问一个工程问题：四个各自固定、对称的 subpixel offsets 分别 render，再在 scene-linear RGB 中等权平均，能否保留 exact repeatability 并降低单点代价？

候选点在输出前固定为 `(-.25,-.25)、(-.25,.25)、(.25,-.25)、(.25,.25)`，权重各 `0.25`。A/B 两组各用四个全新 Blender PID；每个 point process 渲染 derivation frame 37、72、103。共 8 PID、24 次 EXR32 render。reference、NATURAL32 与 CENTER32 复用 B31 derivation 的冻结本地输出，不计入 B32 新样本。

## 观察

四点 ensemble 的 A/B scene-linear RGB 在三帧全部 float exact。相对 B31 双 NATURAL1024 reference proxy：

| frame | NATURAL32 edge RMSE | CENTER32 edge RMSE | QUADRATURE4 edge RMSE | Q4 / NATURAL | Q4 / CENTER |
|---|---:|---:|---:|---:|---:|
| 37 | 0.01169878 | 0.02615864 | 0.01463431 | 1.2509× | 0.5594× |
| 72 | 0.01286223 | 0.02813682 | 0.01528887 | 1.1887× | 0.5434× |
| 103 | 0.01393324 | 0.03152142 | 0.01776561 | 1.2751× | 0.5636× |

mean Q4/NATURAL edge ratio `1.2382×`；mean Q4/CENTER edge ratio `0.5555×`。因此四点合成消除了单点 CENTER edge error 的约 44%，但仍比 NATURAL32 reference error 高约 19–28%。全局 Q4/NATURAL ratio 更接近 1，为 `1.0224–1.0512×`。

观察到的 render-time ratio 为 `4.093×`：四点两组累计 4.509 秒，B31 NATURAL32 两组累计 1.102 秒。它符合四次独立 render 的工程成本预期，但不包含调度、I/O、合成或长序列摊销后的完整成本。

独立验证再用 factory-startup Blender 5.2 运行 analyzer，产生与封存 `analysis.json` byte-exact 的 SHA-256 `5f49a5ad…a9e0cb`。三个轻量负向攻击也均被拒绝：非法 point `Q9`、改写 frame 集为 `37/72/104`、以及非空 output directory。这些攻击只验证了输入边界，不是对数值结论的额外确证。

## 能说与不能说

可以说：在三个 derivation frame 上，预选四点等权 scene-linear ensemble 同时获得 A/B float exact，并把单点 CENTER 的 edge-reference RMSE 降至约 54–56%，代价约 4.09× NATURAL render time。

不能说：四点已经通过未见帧、已达到 NATURAL32 质量、肉眼不可区分、适合电影生产，或四点/等权是最优设计。reference 仍是 proxy；没有 temporal sequence 或 human review。

下一步应先比较一个均匀覆盖 sample square 的 8-point stratified candidate。如果 8-point 只带来很小增益，应优先冻结 4-point 的成本/质量 holdout；如果显著逼近 NATURAL32，则把 4× 与 8× 同时带入正式成本门，不能只选更漂亮的误差数字。

- result SHA：`79b020ff26eb389447c2642e41c6ad4a40370f57074ddf5362f9b0595da45bae`；
- analysis SHA：`5f49a5ad88374a0421375d3d4bedb7ea3eb9dd3b38f725df653bf2ce49a9e0cb`；
- renderer SHA：`dc4a4a2d06b533ac2d541457ebb3a0dce089cd45489af649b987e4e13bc173cc`；
- analyzer SHA：`a874eecdbe0bf915a941de66e235225ea03e9d37a184aaebc2a25fdbebafd7ad`。
- runner SHA：`5a25ffd22d98eb20d17248a452dda05df6f470f104c0667d7974b535beec99d8`。

Artifacts: `experiments/quadrature-derivation-v0-1/results.json`, `experiments/quadrature-derivation-v0-1/analysis.json`, `experiments/quadrature-derivation-v0-1/evidence/`, `blender/render_b32_quadrature_derivation.py` and `blender/analyze_b32_quadrature_derivation.py`.
