# PC.0 C1 attempt-02：hero asset / action inventory PASS

Date: 2026-08-31
Gate: `PC.0`
Verdict: `PASS`

## Result

Fresh attempt-02 使用 accepted arm64 product binary 对 exact frozen B62 scene 完成一次 background、zero-render、zero-save inventory。Runner receipt self hash 为 `c2a979f5…`；独立 audit 27/27 PASS，self hash `ece09ea4…`；sealed root manifest self hash `b33e720f…`。Source SHA-256 前后均为 `0acd4d13…`，external work root 0 files，render-like artifacts 0。

Observed process为1 Blender start、0 render/save/engine/network/model/mouse；wall 0.943 seconds，peak RSS 256,475,136 bytes，均低于冻结上限。Attempt-01 retained failure roots保持exact不变。

## What the inventory explains

Scene共有78 objects、66 meshes、15,734 polygons、12 materials、0 modifiers。66个mesh中33个都只有98 polygons，另有12个为170、9个为338；12个material全部只有2个nodes。这与owner观察到的“建模太粗糙”一致：问题不是没有对象，而是大量hero silhouette由重复的低复杂度 primitive footprints与单一区域材质构成，表面层次、连接结构和近景读形不足。

Animation共有12 actions、67 F-curves、968 keyframes，但9个animated object targets中4个是camera；其余主要集中在guardian rig、core、hand socket和两个IK controls。数量看似不低，观感仍简单的原因是非camera causal targets与secondary-motion categories过于集中，缺少console mechanics、armor/visor response、手部细分与activation-aftershock等分层事件。

## Next gate

PC.1 必须先version-freeze modeling increment及其auditor，然后在fresh derived scene中增加至少12个可命名semantic detail components、至少3个新hero material regions，并在至少2个protected shot views中形成可见silhouette或surface improvement。Camera/light sentinel identities、PB.5 restart safety、PB.6 frame-288 rejection与原始B62/PB evidence全部保持不变。PC.1完成前不启动PC.2 action mutation。

This PASS is an exact baseline inventory for one inherited stylized slice on one admitted host; it is not a final-quality or production-readiness claim.
