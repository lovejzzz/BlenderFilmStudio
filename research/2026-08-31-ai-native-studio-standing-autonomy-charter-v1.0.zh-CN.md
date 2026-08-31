# AI Native Film Studio 持续自主授权章程 v1.0

日期：2026-08-31  
状态：`ACTIVE_STANDING_AUTHORITY`

## 为什么之前总要逐字授权

这不是 Codex 对普通代码修改的固有要求，而是本研究仓库此前为了让每次实验可审计，把授权文本、哈希、运行次数和路径都冻结进了执行合同。这样可以证明某次运行没有越权，但也把正常的迭代变成了反复复制长授权句。

Owner 现明确要求修改这一设定：

> 我没搞懂，为什么你总需要授权？我想改一下这个设定，你可以全权负责

本章程将其落实为持续授权。旧合同和失败证据不改写；未来通过版本化适配器绑定本章程，不再冒充旧的逐字授权已经提供。

## 从现在起默认自主推进

在 BlenderFilmStudio 与 film-engine 项目范围内，Codex 可以不再逐次询问而直接：

- 读取、修改项目源码、测试、协议、文档、脚本、资产与配置；
- 建立 fresh work/evidence roots，构建、测试、启动 Blender、渲染、做基准与独立审计；
- 使用 `caffeinate` 等非破坏性主机控制；
- 在版本化协议记录身份、大小与来源后读取网络、下载公开源码和依赖；
- 创建普通 Git commit，并在验证通过后向现有两个项目仓库做非 force 的 fast-forward push；
- 创建普通分支/PR、发布研究证据与 CI 结果；
- 自主推进后续 Phase B gates；失败时保留 immutable evidence，在 fresh roots 中做最小版本化修正并继续。

## 仍会单独确认的少数高影响动作

以下动作仍需具体确认，因为它们具有破坏性、费用、身份、法律或公开分发影响：

- 购买、付费服务、新 billable resource、收费 LFS/storage/bandwidth；
- 删除/重建/转移/重命名仓库、修改可见性、删除重要用户数据；
- force-push、改写公开历史、删除 ref/tag、绕过分支保护；
- 创建公开二进制 release、分发 DMG、签名、公证或改变 Gatekeeper；
- 修改凭据、账户、组织、账单、安全或访问控制；
- 对外发消息、代表 owner 接受法律条款或作合规承诺；
- 明显超出 BlenderFilmStudio/film-engine 范围或突破冻结资源上限。

## 证据和安全不降低

持续授权只取消重复提问，不降低科学门槛：历史 spec/evidence 仍不可原地修改；新运行仍需 preregistration、fresh roots、资源上限、失败保留与独立审计。OpenAI 平台、系统、工具和安全规则继续有效，仓库章程不能覆盖它们。

本章程不代表项目已经达到生产、分发、法律合规或自主制片水平。
