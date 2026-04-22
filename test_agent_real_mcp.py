#!/usr/bin/env python3
"""
测试智能体是否能正确调用真实的麦当劳MCP工具
"""

import requests
import json
import time

# 服务地址
url = "http://127.0.0.1:8080/process"

# 构造请求 - 要求智能体查询附近门店
data = {
    "input": [
        {
            "role": "user",
            "type": "message",
            "content": [
                {
                    "type": "text",
                    "text": "我在北京西直门，请帮我查一下附近有哪些麦当劳门店可以到店取餐。"
                }
            ]
        }
    ],
    "session_id": "test-real-mcp-session",
    "user_id": "test-real-mcp-user"
}

headers = {
    "Content-Type": "application/json"
}

print("=" * 80)
print("智能体调用真实麦当劳MCP测试")
print("=" * 80)
print(f"\n请求内容:")
print(f"  文本: {data['input'][0]['content'][0]['text']}")
print(f"  Session ID: {data['session_id']}")
print(f"  User ID: {data['user_id']}")
print(f"\n发送请求到: {url}")
print("-" * 80)

try:
    response = requests.post(url, json=data, headers=headers, stream=True, timeout=60)
    
    print(f"\n响应状态: {response.status_code}")
    print(f"响应流开始...\n")
    
    line_count = 0
    tool_calls = []
    responses = []
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            line_count += 1
            
            if line_str.startswith('data:'):
                try:
                    json_str = line_str[5:].strip()
                    data_obj = json.loads(json_str)
                    
                    # 检查响应类型
                    if data_obj.get("object") == "response":
                        status = data_obj.get("status")
                        if status in ["created", "in_progress"]:
                            print(f"[{line_count}] 响应状态: {status}")
                    
                    elif data_obj.get("object") == "message":
                        role = data_obj.get("role")
                        msg_type = data_obj.get("type")
                        print(f"[{line_count}] 消息: role={role}, type={msg_type}")
                        
                        # 检测工具调用（plugin_call 或 tool_call）
                        if msg_type in ["plugin_call", "tool_call"]:
                            tool_name = data_obj.get("tool_name") or data_obj.get("name")
                            if tool_name:
                                tool_calls.append(tool_name)
                                print(f"         *** 工具调用: {tool_name} ***")
                    
                    elif data_obj.get("object") == "content":
                        content_type = data_obj.get("type")
                        if content_type == "text":
                            text = data_obj.get("delta") and data_obj.get("text", "")[:100]
                            if text:
                                print(f"[{line_count}] 文本内容: {text}...")
                                responses.append(text)
                        elif content_type in ["tool_call", "plugin_call"]:
                            tool_name = data_obj.get("tool_name") or data_obj.get("name")
                            tool_calls.append(tool_name)
                            print(f"[{line_count}] *** 工具调用: {tool_name} ***")
                    
                    elif data_obj.get("object") == "tool_result":
                        tool_name = data_obj.get("tool_name")
                        print(f"[{line_count}] 工具结果: {tool_name}")
                    
                except json.JSONDecodeError:
                    pass
    
    print("\n" + "=" * 80)
    print("测试结果总结:")
    print("=" * 80)
    print(f"总响应行数: {line_count}")
    print(f"工具调用: {tool_calls if tool_calls else '无'}")
    print(f"响应内容行: {len(responses)}")
    
    if tool_calls:
        print(f"\n✓ 成功！智能体调用了MCP工具:")
        for tool in tool_calls:
            print(f"  - {tool}")
    else:
        print(f"\n⚠️  警告：智能体未调用任何工具")
    
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"\n✗ 请求失败: {e}")
    print("=" * 80)
