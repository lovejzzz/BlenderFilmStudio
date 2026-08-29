# B61-E1-D2：Blender `--` 参数切片修正预注册

日期：2026-08-29

状态：PREREGISTERED

D1只允许一个Blender start。该进程在0.45秒以exit 2结束、render call为0；stdout/stderr/process均已保留。错误发生在EXR绑定或OpenImageIO import之前：probe使用无参数的`parse_args()`读取Blender完整`sys.argv`，没有把最后一个`--`之后的三个probe参数显式传给argparse。

D1 root不得复用。D2只允许两项变更：probe从最后一个`--`切出其后参数再交给argparse；runner绑定D1 failure tree并改用fresh `experiments/b61-exr-reopen-diagnostic-v0-2`。解码算法、输入EXR、一次Blender/零render/30秒/1 MiB上限和所有接受条件完全不变。

D2仍只是decoder diagnostic。即使PASS也不自动修改B61正式工具，不授权formal v0.3；正式修正仍须单独预注册。
