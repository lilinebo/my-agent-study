import re
from typing import Any, Dict, List, Optional,Tuple
from hello_agent import PlanAndSolveAgent,HelloAgentsLLM,Config,Message,ToolRegistry

# 默认规划器提示词模板
DEFAULT_PLANNER_PROMPT = """
你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。
你的输出必须是一个Python列表，其中每个元素都是一个描述子任务的字符串。

问题: {question}

请严格按照以下格式输出你的计划:
```python
["步骤1", "步骤2", "步骤3", ...]
```
"""

# 默认执行器提示词模板
DEFAULT_EXECUTOR_PROMPT = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
请你专注于解决"当前步骤"，并仅输出该步骤的最终答案，不要输出任何额外的解释或对话。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请仅输出针对"当前步骤"的回答:
"""
class MyPlanAndSolveAgent(PlanAndSolveAgent):
    """
    重写的Plan and Solve Agent - 具备规划和执行能力的智能体
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 5,
        custom_planner_prompt: Optional[str] = None,
        custom_executor_prompt: Optional[str] = None
    ):
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.current_history: List[str] = []
        self.planner_prompt_template = custom_planner_prompt if custom_planner_prompt else DEFAULT_PLANNER_PROMPT
        self.executor_prompt_template = custom_executor_prompt if custom_executor_prompt else DEFAULT_EXECUTOR_PROMPT
        print(f"✅ {name} 初始化完成，最大步数: {max_steps}")
    
    def run(self, input_text: str, **kwargs) -> str:
        """运行Plan and Solve Agent"""
        self.current_history = []
        current_step_index = 0

        print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

        # 规划阶段
        plan_prompt = self.planner_prompt_template.format(question=input_text)
        plan_response = self.llm.generate(plan_prompt)
        try:
            plan = eval(re.search(r'```python(.*?)```', plan_response, re.DOTALL).group(1).strip())
            if not isinstance(plan, list):
                raise ValueError("计划输出不是一个列表")
        except Exception as e:
            print(f"❌ 解析计划失败: {e}")
            return "无法生成有效的计划。"

        print(f"📋 生成的计划: {plan}")

        # 执行阶段
        while current_step_index < len(plan) and current_step_index < self.max_steps:
            current_step = plan[current_step_index]
            executor_prompt = self.executor_prompt_template.format(
                question=input_text,
                plan=plan,
                history=self.current_history,
                current_step=current_step
            )
            step_response = self.llm.generate(executor_prompt)
            self.current_history.append(f"步骤: {current_step} -> 结果: {step_response}")
            print(f"✅ 完成步骤 {current_step_index + 1}: {current_step} -> 结果: {step_response}")
            current_step_index += 1

        final_answer = self.current_history[-1].split("->")[-1].strip() if self.current_history else "未能完成任何步骤。"
        print(f"\n🎯 最终答案: {final_answer}")
        return final_answer