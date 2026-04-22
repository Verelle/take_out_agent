#!/usr/bin/env python3
"""
验证修正后的MCP工具调用方式
测试 tools/call 标准方法是否能正确调用麦当劳真实MCP服务
"""

import os
import sys
import json
import logging

# 添加 deploy_starter 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'deploy_starter'))

from mcp_client import McpClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_real_mcp_server():
    """测试真实的麦当劳MCP服务器"""
    
    # 从 config.yml 读取真实MCP配置
    base_url = "https://mcp.mcd.cn"
    token = "iafsHcMfvAEWtcTO6FTtc40jBuAl63VF"
    
    print(f"测试真实麦当劳MCP服务器")
    print(f"URL: {base_url}")
    print(f"=" * 60)
    
    try:
        # 初始化MCP客户端
        print("\n[1] 初始化MCP客户端...")
        mcp_client = McpClient(base_url=base_url, token=token, timeout=15)
        
        if not mcp_client.handshake_success:
            print("✗ 握手失败")
            return False
        
        print(f"✓ 握手成功")
        print(f"  可用工具数: {len(mcp_client.tools_cache)}")
        
        # 列出所有可用工具
        print("\n[2] 可用工具列表:")
        for tool in mcp_client.tools_cache:
            tool_name = tool.get("name", "unknown")
            description = tool.get("description", "")[:60]
            print(f"  - {tool_name}: {description}...")
        
        # 测试工具调用
        print("\n[3] 测试 query-nearby-stores 工具...")
        print("-" * 60)
        
        test_params = {
            "searchType": 2,
            "beType": 1,
            "city": "北京",
            "keyword": "西直门"
        }
        
        print(f"参数: {json.dumps(test_params, ensure_ascii=False)}")
        
        try:
            result = mcp_client.call_tool("query-nearby-stores", test_params)
            
            print(f"\n✓ 工具调用成功！")
            print(f"返回数据:")
            print(json.dumps(result, ensure_ascii=False, indent=2)[:500])
            
            # 检查返回格式
            if isinstance(result, dict):
                if all(k in result for k in ["success", "code", "message", "traceId", "data"]):
                    print(f"\n✓ 返回格式符合麦当劳官方规范")
                else:
                    print(f"\n⚠️  返回格式不完整，缺少字段")
                    print(f"  期望字段: success, code, message, traceId, data")
                    print(f"  实际字段: {list(result.keys())}")
            
            return True
            
        except Exception as e:
            print(f"\n✗ 工具调用失败: {e}")
            return False
            
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("麦当劳真实MCP服务器测试")
    print("=" * 60 + "\n")
    
    success = test_real_mcp_server()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ 测试成功：已成功连接到真实麦当劳MCP服务器")
    else:
        print("✗ 测试失败：请检查网络连接和认证信息")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
