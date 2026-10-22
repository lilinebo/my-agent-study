"""W7D3：注册表契约测试，以及现有工具链的异常复现实验。"""

import pytest

from hello_agents.tools.response import ToolResponse, ToolStatus
from hello_agents.tools.errors import ToolErrorCode
from my_calculator_tool import create_calculator_registry
from tool_chain_manager import ToolChain


def test_calculator_success():
    registry = create_calculator_registry()

    response = registry.execute_tool("my_calculator", "2 + 3 * 4")

    assert isinstance(response, ToolResponse)
    assert response.status == ToolStatus.SUCCESS
    assert response.text == "14"
    assert response.data["output"] == "14"


def test_unknown_tool():
    registry = create_calculator_registry()

    response = registry.execute_tool("unknown_tool", "some input")

    assert isinstance(response, ToolResponse)
    assert response.status == ToolStatus.ERROR
    assert response.error_info["code"] == ToolErrorCode.NOT_FOUND


def test_tool_chain_unknown_tool_reproduces_response_length_error():
    """记录现有缺陷；通过表示复现成功，不表示工具链已修好。"""
    registry = create_calculator_registry()
    chain = ToolChain(name="unknown_tool_experiment", description="未知工具实验")
    chain.add_step("non_existent_tool", "{input}", "step_1_result")

    with pytest.raises(TypeError, match="object of type 'ToolResponse' has no len"):
        chain.execute(registry, "test input")
