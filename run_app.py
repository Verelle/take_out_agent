#!/usr/bin/env python3
"""
启动应用并设置环境变量
"""

import subprocess
import os
import sys

# 设置环境变量
os.environ["DASHSCOPE_API_KEY"] = "sk-160cfb8745b94f8b80032984ac2b254a"
os.environ["MCP_SERVER_URL"] = "https://mcp.mcd.cn"
os.environ["MCP_TOKEN"] = "iafsHcMfvAEWtcTO6FTtc40jBuAl63VF"

print("启动应用...")
print(f"DashScope API Key: {os.environ['DASHSCOPE_API_KEY'][:20]}...")
print(f"MCP Server URL: {os.environ['MCP_SERVER_URL']}")
print()

# 启动应用
try:
    subprocess.run(
        [sys.executable, "main.py"],
        cwd=os.path.join(os.path.dirname(__file__), "deploy_starter")
    )
except KeyboardInterrupt:
    print("\n应用已停止")
