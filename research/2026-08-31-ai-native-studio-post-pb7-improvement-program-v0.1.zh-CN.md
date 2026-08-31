# Post-PB.7 改进计划 v0.1：保住光影和镜头，提升建模与动作

Date: 2026-08-31

Status: `PREREGISTERED_BEFORE_POST_PB7_INSPECTION_OR_MUTATION`

PB.7 已证明当前 B62 slice 作为早期产品原型可读、可看、可接受。Owner 的真实反馈同时给出清晰方向：光影和镜头感是优势；建模粗糙、动作简单是下一版首先要解决的问题。

本计划不把 `YES YES YES YES` 当成“已经足够好”。它把通过和批评同时保留：下一版必须增加真正可见的轮廓、表面与材质层次，并增加非摄影机的叙事动作和 secondary motion；不能只提高 subdivision、移动摄影机或让灯闪得更多来制造指标。

## 顺序

1. `PC.0`：一次 zero-render、zero-save 的只读 Blender inventory，量出 hero assets 的现有拓扑、材质、modifier、animation、F-curves、keyframes、constraints 和九个 sentinel frames 状态。
2. `PC.1`：建模细节增量，最低 12 个 semantic detail components、3 个 hero material regions，至少两个受保护景别能看到真实细节变化。
3. `PC.2`：动作复杂度增量，最低 4 个独立 non-camera channels、4 个叙事阶段、6 个 animated non-camera targets。
4. `PC.3`：fresh integrated slice、机器回归与 delayed human A/B review。

## 受保护优势

WIDE / MEDIUM / CLOSE 的 frame ranges、camera names、sentinel transforms/lenses，以及 lighting transforms/energy/color 默认 exact protected。任何必要改变必须先另行 preregister，不能在看到新画面后偷偷改标准。PB.5 restart safety、PB.6 receipts 和 frame-288 historical rejection 继续保留。

`PC.0` 只允许一次 Blender start、0 render、0 save、0 engine edit/commit/push、0 network/model/mouse。Fresh evidence root 是 `experiments/ai-native-studio-post-pb7/PC.0-2026-08-31-mac-m2max-attempt-01`，上限 16 MiB / 300 秒 / 2 GiB peak RSS。PC.0 audit 未通过前不得开始 PC.1。

结论上限仍是单个 stylized slice、单台 admitted arm64 host 的可测改进，不扩写成 final-film quality、production readiness、public distribution、cross-platform 或 autonomous filmmaking。
