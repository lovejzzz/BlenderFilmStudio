# 你的个人 AI 电影工作室

先打开一部工程，改一个镜头，保存自己的版本。

在 `output/personal-film-studio/` 文件夹中，双击 **Open Film Studio.command** 打开《The Last Signal》，或双击 **Open Little Gravity.command** 打开《Little Gravity》。首次启动若出现 Blender 快速设置，使用默认设置继续即可。工作室在视窗右侧的 **Film Studio** 标签；按 **N** 可以显示或隐藏侧栏。

## 先试这五步

1. 在 **Shots** 中选择镜头，点 **Go to shot**。按空格播放这一镜头对应的时间范围，再按空格停止。
2. 点 **Closer** 把机位拉近，或点 **Warmer** 调暖画面。**Undo revision** 可以撤销方向修改。
3. 在 **Direct the shot** 输入一句话，例如「保持焦距，让镜头更靠近一点」。点 **Ask AI Director**，阅读建议，再点 **Apply proposed change**。AI 使用你已有的 Codex 登录；它会说明这次改哪个镜头、改什么数值。
4. 点 **Render this frame** 查看最终光照、景深和材质。交互视窗为了操作流畅，显示的是材质预览，和最终渲染会有差别。
5. 点 **Save a new version**。新 `.blend` 工程和 `.film.json` 文档会保存在 `~/Movies/Personal Film Studio/` 对应片名的文件夹里。

## 拍一个新角度

**Add coverage shot** 把当前镜头的时长分给两个角度。它沿用同一个场景和物理运动，不会重新模拟整场戏。选择新角度后可以继续调整距离、环绕角度、焦距和对焦。

AI 导演目前支持镜头距离、环绕角度、焦距、对焦、剪切时间偏移、暖度和曝光。你可以用中文或英文描述意图。复杂的物体创建、人物表演和液体效果需要后续扩展；本版遇到超出范围的请求会拒绝执行。

## 做成自己的电影

满意后点 **Render finished movie**。它会先保存独立的渲染快照，再在后台输出 1920 × 818、24 fps 的影片，加入原创合成配乐、音效、片名和淡入淡出。你可以继续编辑；正在渲染的影片使用点击按钮时的版本。

**Open movie folder** 打开这次任务的文件夹，成片在其中的 `output/delivery/`。如果任务中断，**Resume last movie** 会从已校验的完整帧继续。重新渲染一个修改后的版本，应使用 **Render finished movie** 创建新任务。

保存后可用 **Open another film…** 重新打开工程。每次开始使用工作室，先从上面的启动文件进入，这样导演面板会一起载入。直接双击 `.blend` 可能只会打开普通 Blender 界面。

## 两个起点

| 工程 | 时长 | 可以学习和修改的内容 |
| --- | --- | --- |
| The Last Signal | 18 秒，4 个镜头 | 夜景冷暖光、机械细节、微距、景深、缓慢推移和声音收尾 |
| Little Gravity | 16 秒，4 个镜头 | 日光材质、球与多米诺的真实刚体响应、动作剪辑、接触音效 |

这两个工程由同一套程序化资产、镜头和交付模块制作。磁带机是设计好的机械动画；球释放后的运动由 Blender 的 Bullet 刚体模拟产生。两部片子的形状、摄影和声音都保留在可编辑工程和源码里。

本版在这台 Mac 的现有 Film Studio Engine 上运行。无需购买服务；AI 导演使用已有 Codex 账户额度。高清电影渲染需要持续的本地计算，完成时间取决于镜头和机器负载。
