#!/usr/bin/env python3
"""
直接测试所有麦当劳MCP工具，绕过AgentScope智能体
验证是否符合官方文档要求（参数、返回格式）
"""

import os
import sys
import json
import logging

# 添加 deploy_starter 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'deploy_starter'))

from mcp_client import init_mcp_client, McpClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_tool_direct(mcp_client: McpClient, tool_name: str, params: dict):
    """直接测试MCP工具，不经过包装函数"""
    print(f"\n{'='*60}")
    print(f"测试工具: {tool_name}")
    print(f"参数: {json.dumps(params, ensure_ascii=False, indent=2)}")
    print(f"{'='*60}")
    
    try:
        result = mcp_client.call_tool(tool_name, params)
        print(f"✓ 工具调用成功")
        print(f"返回格式:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 验证返回格式是否符合官方文档
        if isinstance(result, dict):
            required_fields = ["success", "code", "message", "datetime", "traceId", "data"]
            missing_fields = [f for f in required_fields if f not in result]
            if missing_fields:
                print(f"⚠️  缺少字段: {missing_fields}")
            else:
                print(f"✓ 返回格式符合官方文档要求")
        
        return True
    except Exception as e:
        print(f"✗ 工具调用失败: {e}")
        return False

def main():
    # 从环境变量读取配置
    base_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
    token = os.getenv("MCP_TOKEN", "test-token")
    
    print(f"MCP Server URL: {base_url}")
    print(f"MCP Token: {token}")
    
    # 初始化MCP客户端
    print("\n[1] 初始化MCP客户端...")
    mcp_client = McpClient(base_url=base_url, token=token, timeout=10)
    
    if not mcp_client.handshake_success:
        print("✗ 握手失败，退出")
        return
    
    print(f"✓ 握手成功，可用工具数: {len(mcp_client.tools_cache)}")
    
    # 列出所有可用工具
    print("\n[2] 可用工具列表:")
    for tool in mcp_client.tools_cache:
        tool_name = tool.get("name", "unknown")
        description = tool.get("description", "")
        print(f"  - {tool_name}: {description[:60]}...")
    
    # 测试每个核心工具
    print("\n[3] 测试核心工具...")
    
    test_cases = [
        # query-nearby-stores: 查询附近门店
        {
            "tool": "query-nearby-stores",
            "params": {
                "searchType": 2,
                "beType": 1,
                "city": "北京",
                "keyword": "西直门"
            }
        },
        # query-meals: 查询菜单
        {
            "tool": "query-meals",
            "params": {
                "storeCode": "STORE001",
                "orderType": 1
            }
        },
        # query-meal-detail: 查询餐品详情
        {
            "tool": "query-meal-detail",
            "params": {
                "code": "MEAL001",
                "orderType": 1
            }
        },
        # calculate-price: 计算价格
        {
            "tool": "calculate-price",
            "params": {
                "storeCode": "STORE001",
                "orderType": 1,
                "items": [
                    {
                        "productCode": "PROD001",
                        "quantity": 1
                    }
                ]
            }
        },
        # query-store-coupons: 查询门店优惠券
        {
            "tool": "query-store-coupons",
            "params": {
                "storeCode": "STORE001",
                "orderType": 1
            }
        },
        # available-coupons: 可领优惠券（无参数）
        {
            "tool": "available-coupons",
            "params": {}
        },
        # query-my-coupons: 我的优惠券（无参数）
        {
            "tool": "query-my-coupons",
            "params": {}
        },
        # campaign-calendar: 活动日历（无参数）
        {
            "tool": "campaign-calendar",
            "params": {}
        },
    ]
    
    success_count = 0
    for test_case in test_cases:
        tool_name = test_case["tool"]
        params = test_case["params"]
        if test_tool_direct(mcp_client, tool_name, params):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"测试结果: {success_count}/{len(test_cases)} 工具测试成功")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
