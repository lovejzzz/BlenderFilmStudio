# Repository Readiness C2：bundle verify argv correction

状态：**在 attempt-03 tool mutation 前预注册**

日期：2026-08-30

父修正：`research/2026-08-30-post-f0-repository-readiness-c1-bundle-context.md`

修正合同：`specs/ai-native-studio-repository-readiness.v0.3.json`

## 1. Retained attempt-02

attempt-02 tool freeze commit为`4599b3955a6a2083eccaf2349956b0462460ce4b`。它正确执行了C1的fresh root、retained mirror本地clone与official origin恢复；work mirror仍是non-shallow且包含两个prerequisite，bundle SHA-256仍exact为`8018e8b4…`。但实现只把bundle verify的stdout/stderr改成可检查结果，实际argv仍是：

`git bundle verify <bundle>`

而不是C1已冻结的：

`git -C <work-mirror> bundle verify <bundle>`

所以它再次在research repository context得到同一预期拒绝。手工只读复核表明，给同一个attempt-02 mirror和bundle加上`-C`立即`is okay`。

attempt-02永久保留为FAIL：

- failure file SHA-256：`376b1940b1560bbec38bacf3076e078e3ade52b3b58347cc0056425a9b5af272`
- failure receipt hash：`a7f60c832443d2e59d3af425892c4d610a2fe52b51a19d5500cab1debcf9021b`
- source inventory receipt hash：`e73c66517e329914b1d8bd141c39004cac50fc2a3e19a8eede8c5a2f8f8b8927`
- local destination：ABSENT
- second network mirror clones / external creates / external pushes / LFS uploads / Phase B mutations：`0 / 0 / 0 / 0 / 0`

## 2. 唯一允许的 correction

C2只允许：

1. spec切到v0.3与fresh attempt-03 roots；
2. retained input切到attempt-02 work mirror与bundle，同时继续绑定attempt-01/02失败链；
3. bundle verify实际argv加入`-C <attempt-03-work-mirror>`；
4. `--self-test`新增argv级断言，要求verify command exact含`-C`、work mirror、`bundle verify`和bundle path；
5. independent audit验证formal command log中的bundle verify context以及0 second network clone。

除此以外，v0.1协议与C1全部输入、门槛、负控、拓扑结论和授权false保持不变。

## 3. Fresh roots

- evidence：`experiments/ai-native-studio-post-f0/repository-readiness-2026-08-30-mac-m2max-attempt-03`
- external：`/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/repository-readiness-attempt-03`
- retained mirror：attempt-02 `blender-github-full-mirror.git`
- work mirror：attempt-03 `blender-github-full-mirror.git`
- local destination：attempt-03 `film-studio-engine-local.git`

attempt-01/02所有文件与refs保持不可修改。
