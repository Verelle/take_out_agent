"""
debug_mcp_init.py - 调试 MCP 初始化问题
"""

import sys
import os
import logging

# 启用调试日志
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

# 添加到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deploy_starter.mcp_client import init_mcp_client, mcp_client

print("="*80)
print("MCP 初始化调试")
print("="*80)

MCP_SERVER = "https://mcp.mcd.cn"
MCP_TOKEN = "iafsHcMfvAEWtcTO6FTtc40jBuAl63VF"

print(f"\n正在初始化 MCP 客户端...")
print(f"  Server: {MCP_SERVER}")
print(f"  Token: {MCP_TOKEN[:20]}...\n")

try:
    result = init_mcp_client(base_url=MCP_SERVER, token=MCP_TOKEN)
    print(f"\ninit_mcp_client 返回值: {result}")
    print(f"mcp_client 全局变量: {mcp_client}")
    if mcp_client:
        print(f"  - handshake_success: {mcp_client.handshake_success}")
        print(f"  - tools_cache: {len(mcp_client.tools_cache) if mcp_client.tools_cache else 0}")
except Exception as e:
    print(f"发生异常: {e}")
    import traceback
    traceback.print_exc()
