#!/usr/bin/env python3
"""
诊断脚本：显示工具调用详情
"""

import requests
import json

url = "http://127.0.0.1:8080/process"

data = {
    "input": [
        {
            "role": "user",
            "type": "message",
            "content": [
                {
                    "type": "text",
                    "text": "帮我查北京西直门的麦当劳。"
                }
            ]
        }
    ],
    "session_id": "diag-session",
    "user_id": "diag-user"
}

headers = {"Content-Type": "application/json"}

print("发送诊断请求...\n")

try:
    response = requests.post(url, json=data, headers=headers, stream=True, timeout=60)
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            
            if line_str.startswith('data:'):
                try:
                    json_str = line_str[5:].strip()
                    data_obj = json.loads(json_str)
                    
                    # 只显示 plugin_call 相关的消息
                    if data_obj.get("object") == "message":
                        msg_type = data_obj.get("type")
                        if msg_type == "plugin_call":
                            print("=" * 80)
                            print(f"发现 plugin_call:")
                            print(json.dumps(data_obj, ensure_ascii=False, indent=2))
                            print("=" * 80)
                    
                    elif data_obj.get("object") == "tool_result":
                        print("=" * 80)
                        print(f"发现 tool_result:")
                        print(json.dumps(data_obj, ensure_ascii=False, indent=2)[:500])
                        print("=" * 80)
                
                except json.JSONDecodeError:
                    pass
    
    print("\n诊断完成")
    
except Exception as e:
    print(f"错误: {e}")
