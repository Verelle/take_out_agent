#!/usr/bin/env python
"""
诊断脚本：验证 ReActAgent 是否正确调用了 MCP 工具
"""
import sys
sys.path.insert(0, r'c:\Users\Vera\.openclaw\workspace\modelstudio-agent-starter\deploy_starter')

import logging
import asyncio
from unittest.mock import patch

# 启用详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# 导入依赖
from mcp_client import (
    init_mcp_client, 
    list_nutrition_foods,
    query_meals,
)
from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
from agentscope.formatter import DashScopeChatFormatter
import os

# 初始化设置
os.environ['DASHSCOPE_API_KEY'] = 'sk-160cfb8745b94f8b80032984ac2b254a'

# 初始化 MCP 客户端
mcp_url = "https://mcp.mcd.cn"
mcp_token = "iafsHcMfvAEWtcTO6FTtc40jBuAl63VF"

print("[SETUP] 初始化 MCP 客户端...")
mcp_success = init_mcp_client(mcp_url, mcp_token)
print(f"[SETUP] MCP 初始化: {'成功' if mcp_success else '失败'}")

# 创建工具集
toolkit = Toolkit()
toolkit.register_tool_function(list_nutrition_foods)
toolkit.register_tool_function(query_meals)

print("[SETUP] 工具注册完成")

# 创建 Agent
agent = ReActAgent(
    name="TestAgent",
    model=DashScopeChatModel(
        api_key="sk-160cfb8745b94f8b80032984ac2b254a",
        model_name="qwen-turbo",
        generate_args={"max_tokens": 2048},
        enable_thinking=True,
        stream=False,  # 禁用流式输出便于测试
    ),
    sys_prompt="""你是一个测试助手。
当用户问关于餐品营养信息时，必须调用 list_nutrition_foods 工具。
当用户问关于菜单时，必须调用 query_meals 工具。
不允许凭空生成任何真实数据。""",
    toolkit=toolkit,
    formatter=DashScopeChatFormatter(),
)

# 追踪工具调用
tool_calls = []
original_use_tools = agent.use_tools

def tracked_use_tools(tool_calls_list):
    """追踪工具调用"""
    for tool_call in tool_calls_list:
        tool_name = tool_call.get("tool_name") or tool_call.get("name")
        tool_calls.append(tool_name)
        print(f"[TOOL-CALL] Agent 调用工具: {tool_name}")
    return original_use_tools(tool_calls_list)

agent.use_tools = tracked_use_tools

# 发送测试消息
async def test():
    print("\n" + "="*60)
    print("测试: 营养信息查询")
    print("="*60)
    
    test_msg = [{"role": "user", "content": "巨无霸有多少卡路里？营养成分如何？"}]
    
    response = await agent(msgs=test_msg)
    
    print(f"\n[RESPONSE]\n{response}\n")
    print(f"\n[ANALYSIS]\n工具调用次数: {len(tool_calls)}")
    if tool_calls:
        print(f"调用的工具: {', '.join(tool_calls)}")
    else:
        print("❌ 没有检测到工具调用 - 智能体可能是凭空生成答案")
    
    return len(tool_calls) > 0

# 运行测试
if __name__ == "__main__":
    result = asyncio.run(test())
    
    print("\n" + "="*60)
    if result:
        print("✓ 诊断结果: 工具调用正常")
    else:
        print("✗ 诊断结果: 工具调用失败 - Agent 没有调用工具")
    print("="*60)
