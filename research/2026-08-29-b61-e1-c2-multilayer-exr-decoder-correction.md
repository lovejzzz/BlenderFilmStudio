# B61-E1-C2：multilayer EXR decoder与canonical number修正预注册

日期：2026-08-29

状态：PREREGISTERED

## 证据链

B61 v0.2由C1准确捕获：首个EXR写完后，`bpy.data.images.load(...).pixels`在该multilayer文件上长度为0。D2真实Blender probe进一步复现其Image size/channels/depth/pixels均为0，同时证明Blender 5.2随附OpenImageIO 3.1.13.1可唯一枚举`BFS_MASTER.Combined.RGBA`，两次独立open均得到相同的1920×1080×4 float32-LE digest `192237bd…`。D3 zero-Blender reconciliation关闭了Python `1.0`与Node `1`造成的self-hash envelope mismatch。

## 唯一授权变更

Render-side与独立EXR auditor都把disk EXR decoder替换为同一套已证明的bundled OpenImageIO算法：枚举subimage/channel；只允许唯一`.Combined` RGBA quartet；float32读取；按R/G/B/A选择；显式C-contiguous little-endian bytes；对此字节流求SHA。运行时必须exact OIIO 3.1.13.1与NumPy 2.3.4。

两段Python在canonical hash前递归把finite integral float规范为integer；其他数值不变。D3已经证明仅此规范化即可让完整retained result的Python与Node hash一致。

三段Node supervision只可绑定C2/D2/D3证据、复核v0.2 retained trees、使用fresh v0.3 roots并新增decoder runtime/channel assertions。

## 不变项

镜头、帧、A/B、64 spp、1080p、Cycles CPU、ACES OCIO、multilayer half-float ZIP、18次render、decoded exact digest、16 gates、10 attacks、timeout、磁盘预算、C1日志/ledger和claim boundary全部不变。不允许把格式降为single-layer，不允许放宽为近似像素或事后容差。

## 执行顺序

先提交推送D3证据与本C2。随后实现五项工具并freeze；fresh-clone zero-Blender rehearsal通过后，主仓库才能签发official v0.3 preflight。只有preflight evidence另行推送后，才能创建v0.3 attempt/formal roots并启动真实Blender矩阵。
