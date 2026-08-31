# PB.2 execution template v0.4

日期：2026-08-31

状态：**模板完成，不可执行**

该模板把 future one-run execution contract 的所有非授权字段和 exact argv 固定下来，包括 tool-freeze commit `92d1aa15…`、两个工具 SHA、B01/B02、八个负控、fresh roots 与全部零权限计数。

四个授权字段和 `researchCommit` 刻意保持 `null`，status 为 `DRAFT_NON_EXECUTABLE_AUTHORIZATION_MISSING`。formal runner 只接受 `AUTHORIZED_FOR_ONE_FORMAL_RUN`，并在 fresh-root 创建和产品模块加载之前检查，因此该模板不能误启动 PB.2。

批准后必须复制为新文件 `specs/ai-native-studio-pb2-validation-only-execution.v0.4.json`，绑定用户原文和包含该文件的研究提交；不得修改或重命名模板本身。
