# PC4-VX1 C2：locked multilayer EXR review adapter

Attempt-02 消费全部六项 plan operation、创建至少 28 个 typed parts 并保存 derivative 后，在第一张 render 前尝试把主 scene 从产品锁定的 `OPEN_EXR_MULTILAYER` 改为 `PNG`，引擎拒绝该 enum。Retained derivative SHA-256 为 `c51a0fbb…`；0 render、0 PNG，source unchanged。Runner failure summary 中的 `sceneMutations: 0` 低估了已发生的一次 derivative save，manifest 与本 correction 以 stdout 和 retained blend 为准，不回写历史 failure。

C2 只改变 review output adapter：主 scene 保持 multilayer EXR，三次各写一个 temporary EXR；读取唯一 Combined RGBA 后在 isolated output scene 使用 admitted `sRGB` / `ACES 2.0` 写 PNG，并立即删除 temporary EXR。这个路径已由 PC.4 C2 在同一 binary 上实测。

Plan、六项 operation、28-part geometry、visibility、12% framing、camera/light/source protection、两次 start、三次 render、一次 save 与直接视觉 review 阈值全部不变。Attempt-02 evidence/work roots immutable；attempt-03 从原始 source 重建。
