# PC8 measured shutter：PASS

## 结论

PC8 在冻结范围内通过。Film Studio Engine 没有给当前作品手填一个“好看”的快门，而是读取 Blender/Bullet 已求解场景在撞击帧的语义物体屏幕运动，用六个刚体的中位速度自动求出原生 transform motion blur 快门。

这关闭的是“运动呈现由真实物理数据驱动”这一层，不是照片级真实感。直接看片确认因果连续、没有最终姿态摆放感、模糊不会遮掉碰撞关系；同时确认瓶状目标仍过于抽象、环境过净、接触链偏整齐。

## retained C2 harness correction

冻结 v0.1 runner 在任何正式 root、构建或产品启动前因 `0.000001` 的 Python/JavaScript 数字拼写差异停止。C2 只修正主机自哈希验证器，并保留原工具不变：

- Python canonical hash：`db3b7ccb9bdbe40dd28202a53e54557db34a64b49a3ea136ef628bd47fb817b8`
- JavaScript canonical hash：`8110fdbb9263fd7c62eb1997b43b6fe92d768bdbae04ddc5aae23f89de74b6ab`
- C2 correction spec hash：`b2ef2f4ab3b6270b996ff61702cab9c0b8325196c6515af224bf4f79ecdfe64e`
- C2 freeze hash：`ec5d9ce8eb83fe44763ede4a88e8239b9e08212ac7adc63ad79e4c2bc2fab067`

产品源码、v0.4 fixture、物理、镜头算法、阈值、资源和正式 roots 均未改变。

## 正式结果

- evidence root：`experiments/measured-shutter/PC8-2026-09-01-attempt-01`
- work root：`/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC8-2026-09-01-attempt-01`
- 产品源码：`9d5a66869528b66216b977c01312cdc849f28fad`
- 产品模块 SHA-256：`009544bd57445b679cc81636d3f18d8bcd492201b2a14a3bc1daa7f40ac484fb`
- 正式 binary SHA-256：`431efe6f5794d768713edb2365d7e69d5975840b4804b7384e082cbdd1b65287`
- receipt hash：`801b2c83d031c210d3e2eb3073aee4e3ad49dbe3889b276e6439bf74c22b7d58`
- independent audit：`27/27 PASS`
- audit hash：`8faff835f653d0bffca847c0a1339e3a474c65d6e950b20a931bc4abf893ae85`
- direct review hash：`e4fb55862a939ec7ab86c4205064c5c5e6ef97c6fcfba0226dfc1d3f38c56f39`
- acceptance hash：`48ab5ec28bd46ce0d361e2e6691f58fa44280faaefe8a8ebecc73d69e797ff69`

一次干净原生构建和三次产品启动完成：16 个负向控制、一次场景生成、一次保存、一次重新打开、一个 sharp impact control、三张产品审阅图和 24 帧撞击片段。网络、engine remote write、force push、tag、release、binary distribution、签名与公证全部为 0。

## 物理与快门

PC7 的初始条件和完整 primary physics 逐值不变：response frames 仍为 `28/29/29/30/31`，impact 仍为 frame 38，aftermath 仍为 frame 86，最终倾角仍为 `90.00°/90.00°/62.69°/62.32°/90.00°`。target pose keys 和 release 后 actor pose keys 都是 0，reopen exact。

软件在 frame 37→38、960×540 的 IMPACT 镜头中测得：

- 六个语义刚体速度范围：`16.25183590–21.45851336 px/frame`
- 中位速度：`19.61656045 px/frame`
- 冻结目标：`6.0 px`
- 自动快门：`0.30586402 frame`
- 实现模糊：`6.00000004 px`
- 误差：`0.00000004 px`

只启用 Blender 原生 transform motion blur；compositor/postprocess blur 为 false。

## 直接视觉判断

同帧 sharp/blurred A/B 中，实测模糊让速度明显增强，但球缝、五个目标、面板、黑色束带与碰撞方向仍清楚。24 帧序列从接触连续进入传播倾倒和散落，没有姿态跳变；aftermath 的支撑、重叠与不同倾角来自 Bullet，而不是人工排列。

不通过照片级质量：当前目标更像 polished wooden blocks，不像具有壁厚、瓶盖、标签、液体或可信重量分布的瓶子；地面与环境太洁净，碰撞链也比真实生活更整齐。运动层升级成功，建模/物性/接触层仍是主要限制。

## 软件学到的规则

1. 从已求解的语义物体屏幕运动推导快门，不给所有项目套固定数值。
2. 用语义物体中位数抵抗单个高速碎片或静态背景对快门的支配。
3. presentation-only 字段不能改变 physical variation identity。
4. measured strategy 下拒绝手填快门与后期假模糊。
5. 每次都绑定同帧 sharp/blurred A/B；数字正确不等于电影信息可读。
6. 下一层必须提升可识别物理原型、尺度/质量/碰撞几何、材质响应与次级接触，同时继续禁止最终姿态权力。

## 下一步

PC9 将把简单课程变成真正可辨认的篮球撞三瓶：由软件依据语义原型生成瓶身、瓶肩、瓶颈、瓶盖/标签和匹配碰撞轮廓，并以尺度感知的质量、摩擦、恢复系数及受限初始差异交给 Bullet。验收仍要求零目标最终姿态 key、连续 clip、重新打开 exact 和直接截图判断。PC4 机器人继续作为后续未见过的 capstone，不在课程阶段手工修片。

## 产品源码发布

验收后的单父提交由 `c7eece67…` 普通 fast-forward 到 `9d5a6686…`，只更新 `lovejzzz/film-engine` 的 `refs/heads/main`。公开 raw 模块 SHA-256 与正式构建绑定的 `009544bd…` 完全一致。第一次命令因 zsh 对未加花括号变量后的冒号解析而在本地拒绝，远端未变；随后只修正 refspec 拼写并成功。force、其他 ref、tag、release、LFS、二进制、签名与公证计数均为 0。
