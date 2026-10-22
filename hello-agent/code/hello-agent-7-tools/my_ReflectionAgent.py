import re
from typing import Any, Dict, List, Optional,Tuple
from hello_agent import Reflectionagent,HelloAgentsLLM,Config,Message,ToolRegistry

MY_REFLECTION_PROMPTS = {
    "initial": """
请根据以下要求完成任务:

任务: {task}

请提供一个完整、准确的回答。
""",
    "reflect": """
请仔细审查以下回答，并找出可能的问题或改进空间:

# 原始任务:
{task}

# 当前回答:
{content}

请分析这个回答的质量，指出不足之处，并提出具体的改进建议。
如果回答已经很好，请回答"无需改进"。
""",
    "refine": """
请根据反馈意见改进你的回答:

# 原始任务:
{task}

# 上一轮回答:
{last_attempt}

# 反馈意见:
{feedback}

请提供一个改进后的回答。
"""
}

class MyReflectionAgent(Reflectionagent):
    """
    重写的Reflection Agent - 具备反思和改进能力的智能体
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        custom_prompts: Optional[Dict[str, str]] = None
    ):
        super().__init__(name, llm, system_prompt, config)
        self.prompts = custom_prompts if custom_prompts else MY_REFLECTION_PROMPTS
        print(f"✅ {name} 初始化完成，使用的提示词集: {list(self.prompts.keys())}")

    def run(self, task: str) -> str:
        """运行Reflection Agent"""
        # 初始回答
        initial_prompt = self.prompts["initial"].format(task=task)
        initial_response = self.llm.generate(initial_prompt)
        
        # 反思阶段
        reflect_prompt = self.prompts["reflect"].format(task=task, content=initial_response)
        feedback = self.llm.generate(reflect_prompt)
        
        # 改进阶段
        refine_prompt = self.prompts["refine"].format(task=task, last_attempt=initial_response, feedback=feedback)
        refined_response = self.llm.generate(refine_prompt)
        
        return refined_response
