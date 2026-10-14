# AI 工程 Skill 库

用途：长期维护可复用的方法与第三方 Agent Skills。安装日期：2026-10-14。

## 安装清单与来源

| Skill | 固定版本来源 | Commit |
| --- | --- | --- |
| [learning-codebases](learning-codebases/SKILL.md) | [Eijnewgnaw/learning-codebases](https://github.com/Eijnewgnaw/learning-codebases/tree/07faad3974ee6238c42d119f6441d46c6134bb2c/skill/learning-codebases) | 07faad3974ee |
| [code-archaeology](code-archaeology/SKILL.md) | [luanluan1/code-archaeology-skill](https://github.com/luanluan1/code-archaeology-skill/tree/14825a6d8ff828c8de0ea42171d1a1bcb0f9cf9c/skill/code-archaeology) | 14825a6d8ff8 |
| [software-architecture-review](software-architecture-review/SKILL.md) | [liza-mas/liza](https://github.com/liza-mas/liza/tree/7e12901e914b014041ddf8c7f45e4ddab07b338d/skills/software-architecture-review) | 7e12901e914b |
| [code-reviewer](code-reviewer/SKILL.md) | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills/tree/c062f9f9a104d9ebf88cefcacc0993e101db5e7c/skills/code-reviewer) | c062f9f9a104 |
| [agent-builder](agent-builder/SKILL.md) | [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code/tree/ce8f9f186058939da54c9d6fead78dfb5d0fd6c3/skills/agent-builder) | ce8f9f186058 |
| [agent-evaluation](agent-evaluation/SKILL.md) | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills/tree/c062f9f9a104d9ebf88cefcacc0993e101db5e7c/skills/agent-evaluation) | c062f9f9a104 |
| [technical-project-management](technical-project-management/SKILL.md) | [magnus919/agent-skills](https://github.com/magnus919/agent-skills/tree/b3b45651ffa2ca882911c2ebfeeab8e3dc7b53ce/technical-project-management) | b3b45651ffa2 |
| [technical-writer](technical-writer/SKILL.md) | [OneWave-AI/claude-skills](https://github.com/OneWave-AI/claude-skills/tree/fc5b7851a6c7ba367e05797df46ad3679df355dd/technical-writer) | fc5b7851a6c7 |
| [mcp-builder](mcp-builder/SKILL.md) | [anthropics/skills](https://github.com/anthropics/skills/tree/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/mcp-builder) | dbd4588f9e10 |
| [systematic-debugging](systematic-debugging/SKILL.md) | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills/tree/c062f9f9a104d9ebf88cefcacc0993e101db5e7c/skills/systematic-debugging) | c062f9f9a104 |

完整路径、版本与许可证说明见 [sources.json](sources.json)。保留上游配套文件和许可证，不执行随附脚本或安装它们的运行依赖。

## 对应学习方向

- 项目学习：learning-codebases（项目地图与证据驱动学习）、code-archaeology（Git 历史与演化）。
- 工程能力：software-architecture-review、code-reviewer。
- AI Agent：agent-builder；agent-evaluator 的需求由 agent-evaluation 实现，保留上游名称。
- 个人成长：project-manager 的需求由 technical-project-management 实现，保留上游名称；technical-writer。
- 额外补充：mcp-builder（MCP 服务设计与工具集成）、systematic-debugging（根因调查与验证）。

## 使用方式

本次安装位置仅为本仓库 skills/，没有安装到用户全局目录。

可以在学习会话中指定完整文件，例如：

> 请读取 skills/learning-codebases/SKILL.md 及其按需引用的文件，按此方法只读学习 hello-agent/code/hello-agent-7。将已验证结论记录到 hello-agent/notes，并区分事实、推测与待验证问题。

建议先使用 learning-codebases，再用 code-archaeology 追踪历史；实践时结合 agent-builder、agent-evaluation 和 systematic-debugging；最后用 technical-writer 整理技术资产。

## 兼容性与使用边界

- software-architecture-review 原文带有 Liza 品牌占位符和专用工具说明。它在此作为评审方法库保存；缺失的 AGENT_TOOLS.md 不能虚构，使用现有文件搜索工具替代专用搜索工具。报告路径按当前任务明确指定。
- technical-project-management 引用了其他专业 Skill 作为任务分流建议，本次不递归安装整套技能库；涉及未安装的专业领域时明确说明限制。
- agent-builder 是最小 Agent 构建方法，工程实践仍需明确工具权限、成本、超时和评估指标。
- 示例中的 SDK 用法需在实际开发时对照当前官方文档验证，本次没有执行示例或声明运行通过。
- 使用企业项目时遵守现有授权范围，不把公司源码、密钥、内部数据或未脱敏资料存入本仓库。
- 安装外部 Skill 不代表执行其中的发送消息、发布、部署或生产操作；实际操作遵循当前任务授权。

## 原有个人方法文档

以下四份原有 Markdown 保留，可结合第三方 Skill 逐步改进：

- [代码库学习](codebase-learning.md)
- [代码评审](code-review.md)
- [架构评审](architecture-review.md)
- [技术写作](technical-writing.md)

## 维护模板

- 更新日期：待填写
- Skill 与旧 / 新版本：待填写
- 更新原因与上游差异：待填写
- 许可证与引用变化：待填写
- 本地使用结果、局限与改进：待填写
