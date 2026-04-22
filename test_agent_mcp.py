#!/usr/bin/env python3
"""
测试智能体是否能正常调用MCP工具
"""

import requests
import json
import time

# 服务地址
url = "http://127.0.0.1:8080/process"

# 构造请求
data = {
    "input": [
        {
            "role": "user",
            "type": "message",
            "content": [
                {
                    "type": "text",
                    "text": "我在北京西直门，帮我找附近的麦当劳门店，要能到店取餐的。"
                }
            ]
        }
    ],
    "session_id": "test-agent-session",
    "user_id": "test-agent-user"
}

headers = {
    "Content-Type": "application/json"
}

print("发送请求到智能体...")
print(f"Request: {json.dumps(data, ensure_ascii=False)}\n")

try:
    response = requests.post(url, json=data, headers=headers, stream=True, timeout=30)
    
    print(f"Status: {response.status_code}")
    print(f"Headers: {response.headers}\n")
    print("Response (流式输出):")
    print("=" * 80)
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data:'):
                try:
                    json_str = line_str[5:].strip()
                    data_obj = json.loads(json_str)
                    print(json.dumps(data_obj, ensure_ascii=False, indent=2))
                except:
                    print(line_str)
            else:
                print(line_str)
    
    print("=" * 80)
    print("\n✓ 请求完成")
    
except Exception as e:
    print(f"✗ 请求失败: {e}")
