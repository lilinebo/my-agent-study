from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM, ToolRegistry
from hello_agents.tools import CalculatorTool
from MyAgent import MySimpleAgent

# 加载环境变量
load_dotenv()

# 创建LLM实例
llm = HelloAgentsLLM()

# 测试1：基础对话agent(无工具)
print("=== 测试1:基础对话 ===")
basic_agent = MySimpleAgent(
    name="基础助手",
    llm=llm,
    system_prompt="你是一个友好的AI助手，请用简洁明了的方式回答问题。"
)

response1 = basic_agent.run("你好，请介绍一下自己",3)
print(f"基础对话响应: {response1}\n")

# 测试2：带工具调用的agent
print("=== 测试2:带工具调用的agent ===")
tool_registry = ToolRegistry()
calculator_tool = CalculatorTool()
tool_registry.register_tool(calculator_tool)

enhanced_agent = MySimpleAgent(
    name="增强助手",
    llm=llm,
    system_prompt="你是一个友好的AI助手，可以使用工具来回答问题。",
    tool_registry=tool_registry,
    enable_tool_calling=True
)
response2 = enhanced_agent.run("请计算 12 * 8",3)
print(f"增强对话响应: {response2}\n")

# 测试3：流式响应
print("=== 测试3:流式响应 ===")
streaming_agent = MySimpleAgent(
    name="流式助手",
    llm=llm,
    system_prompt="你是一个友好的AI助手，请用简洁明了的方式回答问题。",
    enable_tool_calling=False
)
for chunk in streaming_agent.stream_run("请用流式方式回答这个问题：什么是人工智能？"):
    print(f"流式响应片段: {chunk}")

# 动态添加工具
print("\n=== 测试4:动态添加工具 ===")
print(f"动态添加工具前：{basic_agent.has_tools()}")
basic_agent.add_tool(calculator_tool)
print(f"动态添加工具后：{basic_agent.has_tools()}")
print(f"可用工具列表: {basic_agent.list_tools()}")

# 查看历史对话
print("\n=== 测试5:查看历史对话 ===")
for msg in basic_agent.get_history():
    print(f"{msg.role}: {msg.content}")
print(f"\n对话历史: {len(basic_agent.get_history())} 条消息")