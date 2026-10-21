# 2026-10-21：Tool System / Tool Registry——W7D3

## 任务与完成情况

- 日期：2026-10-21，周三；主线：P1 Hello-Agents；章节：第 7 章。
- 核心目标：理解注册、查找、调用和未知工具处理。
- 原计划：源码阅读 15 分钟、两个 pytest 用例 30 分钟、工具链实验 10 分钟，总预算约 60 分钟；这是计划耗时。
- 验收：阅读答案、两个核心测试、异常复现和原因记录已补齐，等待用户复核后提交。
- 本文由 Codex 协助补全并验证。测试通过说明行为得到验证，个人掌握程度仍需闭卷复述。

## 材料与环境

本次依据本机 hello-agents 1.0.1 源码，Python 3.12.9。

- hello_agents/tools/registry.py：register_function、execute_tool、_function_response、未知工具分支。
- hello_agents/tools/response.py：ToolResponse、ToolStatus。
- hello_agents/tools/errors.py：ToolErrorCode。
- [计算器与注册函数](../code/hello-agent-7/my_calculator_tool.py)。
- [工具链实现](../code/hello-agent-7/tool_chain_manager.py)。
- [本次测试](../code/hello-agent-7/test_tools.py)。

源码按符号名定位，避免原任务行号随安装包变化失效。测试未调用模型或外部业务接口。

## 阅读答案：两条查找路径

| 比较项 | _tools | _functions |
| --- | --- | --- |
| 注册入口 | register_tool(tool) | register_function(func, name=..., description=...) |
| 保存内容 | 名称到 Tool 对象的映射 | 名称到包含 func、description 的字典的映射 |
| 查找顺序 | execute_tool 先检查此表 | 前一个分支未命中时再检查此表 |
| 输入处理 | 解析或整理为参数字典 | 本次同步普通函数路径直接传入 input_text |
| 执行方式 | tool.run_with_timing(parameters) | func(input_text)，再包装返回结果 |

本机实现默认拒绝同名注册冲突。计算器注册在 _functions 中。

execute_tool 返回 ToolResponse，成功和未知工具两种情况都如此：

- status：ToolStatus.SUCCESS、PARTIAL 或 ERROR。
- text：可阅读文本。
- data：结构化结果；本次计算器为 {"output": "14"}。
- error_info：错误信息；未知工具包含 code="NOT_FOUND"。
- stats、context：运行统计和上下文。

默认配置下，两张表都未找到工具时，返回错误响应，而非直接抛出“找不到工具”的 Python 异常。

## 正常调用链与首次错误

```text
create_calculator_registry()
→ 创建 ToolRegistry 实例
→ register_function 将 my_calculate 注册为 my_calculator
→ 同一个实例 execute_tool("my_calculator", "2 + 3 * 4")
→ 命中 _functions，执行 my_calculate(input_text)
→ 原始函数返回字符串 "14"
→ 包装为 ToolResponse(status=SUCCESS, text="14", data={"output": "14"})
```

首次练习中 from hello_agents.tools import registry 导入的是模块，不是注册表实例。因此直接 registry.execute_tool(...) 实际先报：

```text
AttributeError: module 'hello_agents.tools.registry' has no attribute 'execute_tool'
```

正确做法是使用 create_calculator_registry() 返回的实例。仅创建空实例而不注册计算器，也不能完成正常调用。

## 测试与实测结果

1. test_calculator_success：断言返回类型、成功状态、文本 14 和结构化输出。
2. test_unknown_tool：断言返回类型、错误状态及 NOT_FOUND 错误码。
3. test_tool_chain_unknown_tool_reproduces_response_length_error：捕获现有工具链的 TypeError，保留可重复的实验。

前两个是作业核心测试。第三个测试通过表示异常复现成功，不表示工具链已经修好。

全局 Python 缺少 pytest，本次将 pytest 9.1.1 安装到工作区临时目录，未修改全局环境。仓库根目录下用 PowerShell 运行：

```powershell
# 首次准备环境；已有该目录时无需重复安装。
python -m pip install --target D:\vsproject\tmp\w7d3-pytest pytest==9.1.1
$env:PYTHONPATH = 'D:\vsproject\tmp\w7d3-pytest'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -B -m pytest -p no:cacheprovider hello-agent/code/hello-agent-7/test_tools.py -v
```

2026-10-21 实测：3 passed in 0.25s。只运行本作业文件，禁用第三方插件自动加载，避免执行其他需要模型配置的演示脚本。临时依赖不属于本仓库提交内容。

## 工具链实验与原因

使用正确注册表实例，创建只包含 non_existent_tool 的工具链，传入 test input。实际异常：

```text
TypeError: object of type 'ToolResponse' has no len()
```

出错位置为 ToolChain.execute 的 len(result)：

```text
未知工具
→ Registry 返回 ToolResponse(status=ERROR, code=NOT_FOUND)
→ ToolChain 将对象保存到 context
→ 打印日志时调用 len(result)
→ ToolResponse 没有长度协议，抛出 TypeError
```

Registry 已正常表达未知工具错误；随后是调用方错误地把响应对象当字符串，导致崩溃。成功响应也是 ToolResponse，同样不能直接求长度。

修复方向：先检查 status，明确失败时是否停止；成功时再选择 text 或约定的结构化数据供后续步骤使用。仅改为 len(result.text) 只解决日志崩溃，未解决失败处理。本次按作业要求保留现有实现以复现问题，修复留作后续练习。

## 复盘与自测

已验证：正常计算返回成功响应；未知工具返回 NOT_FOUND；工具链在 len(result) 处抛出 TypeError。

源码观察（本次未新增测试）：my_calculate 捕获异常后返回“计算失败”字符串，注册表可能仍将它包装为 SUCCESS。业务失败应通过明确的响应状态表达，不能只依靠错误文案。

闭卷自测：

1. 模块 registry、类 ToolRegistry、注册表实例有何区别？
2. 为什么注册和调用必须使用同一个实例？
3. 为什么返回 ERROR 不等于向调用方抛出异常？
4. 为什么成功响应也不能直接 len(response)？
5. 修工具链时，除了日志还必须决定什么失败处理行为？
