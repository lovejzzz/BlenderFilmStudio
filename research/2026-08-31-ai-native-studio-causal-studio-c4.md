# PC5 C4：物理后语义取景与跨语言数值证据

Attempt-04 首次完成两次真实 Bullet 求解和三张截图。物理结果非常清楚：首次目标响应在 28 帧，随后两瓶均在 29 帧响应；120 帧三瓶倾角为 89.63°、89.64°、89.75°，reopen 精确复现。机器审计 19/20，唯一失败是 Python/JavaScript 对非整数 float 的最短十进制/指数 spelling 不同。直接看图则为视觉失败：SETUP/IMPACT 可读，AFTERMATH 固定相机仍指向原始瓶子位置，真实物理已把目标推到 x=3.58..6.03，结果镜头几乎全空；SETUP 右上还有 cyclorama 黑楔穿帮。

C4 教软件一条通用规则：每个 review frame 在物理求值后，使用所有叙事物体的 evaluated world bounds 重新计算中心、相机距离、屏幕 occupancy 与 negative-space margin。相机保持该 shot 的视角方向和焦段性格，但不再假设主体仍在初始坐标。不得读取 attempt ID、瓶子最终坐标或截图像素去写固定机位。背景改为无穿帮的简单摄影棚墙；它不参与物理。

证据修正把 Python 输出记录中的 float 在写入和 self-hash 前确定性转成十进制字符串，避免跨语言 number serializer 差异；物理审计仍显式转回 Number 比较门槛。模型、刚体参数、发射、三瓶 60° 门槛、灯光、三个 review frames、render 尺寸和资源上限不变。Attempt-05 使用 fresh roots，attempt-01..04 保持不变。
