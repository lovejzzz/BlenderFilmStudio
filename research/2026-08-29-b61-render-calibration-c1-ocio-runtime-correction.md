# B61 校准 C1：重开 `.blend` 时显式恢复冻结 OCIO 环境

日期：2026-08-29

状态：v0.2 执行前预注册

## v0.1 反例

`experiments/b61-render-calibration-v0-1` 的两个 Blender 进程都 exit 0 并写出 EXR，但每次重开 `.blend` 都出现四条 color-management fallback warning：

1. `sRGB - Display` 回退为 `sRGB`；
2. `ACES 2.0 - SDR 100 nits (Rec.709)` 回退为 `ACES 2.0`；
3. scene output display 同样回退；
4. `Un-tone-mapped` output view 回退为 `Standard`。

因此 v0.1 的两个 EXR 和 timing 对冻结的 ACES 管线均不可准入。Self-hashed failure receipt 为 `e5ab5bfae81b90e7af855c18b0d91dbc66bf4438fb2f74f6190808a2cc8d2456 / 52322c6ef2f8e8442d7ab13341c3f9fd562a75c41bd3697059b50593c705ad38`。整个 v0.1 root 固定为 7 files / 2,752,881 bytes / tree hash `2c0623c37ebe8d6b9d4d3bed3ac214af91da5102936acbccb96b43ba6832ffe8`，不得删除、覆盖或复用。

## 根因

Production compiler 启动 Blender 时在 `scripts/run-restricted-blender-compile.mjs` 中显式注入 `OCIO=<verified config path>`；独立渲染命令遗漏了同一运行时环境。`.blend` 保存的是 display/view 名称，不会打包外部 OCIO 配置。重新打开时若没有正确环境，Blender 会在读取 scene 的早期阶段自动回退。

## 唯一授权修正

v0.2 使用 fresh root `experiments/b61-render-calibration-v0-2`，保持 source blend、frame、resolution、samples、engine/device、format、timeout 和操作上限完全不变。唯一环境修正为在 Blender 进程启动前设置：

`OCIO=/Users/tianxing/CodexProjects/FilmMaking/Reference/BlenderFilmStudio/color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio`

配置文件必须先重算 SHA-256 并 exact 等于 `24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15`。

## 新增 fail-closed 检查

每个 Blender 进程在 render 前必须断言：

- `scene["bfs_ocio_sha256"]` 等于冻结配置 SHA；
- `scene["bfs_ocio_config"]` 等于 `cg-config-v4.0.0_aces-v2.0_ocio-v2.5`；
- `scene.display_settings.display_device` 等于 `sRGB - Display`；
- `scene.view_settings.view_transform` 等于 `ACES 2.0 - SDR 100 nits (Rec.709)`；
- stdout 不包含 `color_management | WARNING`。

任一断言、进程或文件检查失败，v0.2 标记 FAIL 并保留输出，不允许再修补该 root。

## 结论边界

v0.2 若通过，只使资源 timing 对已冻结 OCIO 管线有效；仍不产生 B61 正式像素复现或 cinema-quality verdict。正式 B61 仍需独立预注册。
