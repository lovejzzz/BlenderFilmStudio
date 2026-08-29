# B62-P0-E1-C2：fresh-clone Node 依赖隔离更正

Date: 2026-08-29

Status: **preregistered after failed rehearsal, before retry, before official preflight and before any B62 Blender process**

## 保留的失败

tool freeze `37d9524…` 推送后，在 `/tmp/b62-rehearsal-37d9524` 从本机仓库创建全新 clone。第一次 zero-Blender preflight 在 Node 模块加载阶段以 `ERR_MODULE_NOT_FOUND: ajv` 退出；preflight root 尚未创建，attempt/formal roots absent，Blender starts/renders均为0。

根因不是 B62 合同需要 Ajv，而是三个 B62 Node entry points 为取得 `repositoryRoot`，导入了通用 `scene-spec.mjs`；后者在模块顶层导入 Ajv。主工作树已有 `node_modules`，因此静态检查没有暴露 clean-clone 缺陷。

## 唯一授权的更正

三个 B62 Node entry points 改为只用 Node built-ins 从各自 `import.meta.url` 推导仓库根路径，并把本 C2 文档加入冻结工具集合与 ancestry 检查。禁止在 rehearsal clone 安装或软链接 `node_modules`；禁止改变资产、帧、samples、timeout、预算、18 gates、16 attacks或verdict。

修改后必须产生新的tool-freeze commit并推送，再从另一个fresh local clone重做zero-Blender rehearsal。失败clone不得成为official evidence。正式三棵root名称保持不变，因为此前从未创建。
