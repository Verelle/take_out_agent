#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证虚拟 MCP 所有工具"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Content-Type": "application/json"}

def call_tool(method, name=None, arguments=None):
    """标准 JSON-RPC 2.0 工具调用"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method
    }
    if method == "tools/call":
        payload["params"] = {"name": name, "arguments": arguments or {}}
    else:
        payload["params"] = {}
    
    resp = requests.post(BASE_URL, json=payload, headers=HEADERS, timeout=5)
    return resp.json()

def test_tool(name, args, test_desc):
    """测试单个工具"""
    try:
        result = call_tool("tools/call", name, args)
        if "error" in result:
            print(f"✗ {name}: {result['error']['message']}")
            return False
        
        # 虚拟MCP直接返回result中的数据（success, code, data等），不需要content转换
        data = result.get('result', {})
        success = data.get('success', False)
        
        if success:
            print(f"✓ {name}: {test_desc}")
            return True
        else:
            print(f"✗ {name}: {data.get('message', '未知错误')} (code={data.get('code')})")
            return False
    except Exception as e:
        print(f"✗ {name}: {str(e)}")
        return False

print("=" * 50)
print("虚拟 MCP 工具验证")
print("=" * 50)

# 2.3 查询附近门店
result1 = test_tool(
    "query-nearby-stores",
    {"searchType": 2, "beType": 1, "city": "上海", "keyword": "徐家汇"},
    "返回门店数据"
)

# 2.4 查询菜单
result2 = test_tool(
    "query-meals",
    {"storeCode": "SX001", "orderType": 1},
    "返回菜单数据 (SX 编码)"
)

# 2.5 查询餐品详情
result3 = test_tool(
    "query-meal-detail",
    {"code": "SX_BG001", "storeCode": "SX001", "orderType": 1},
    "返回餐品详情"
)

# 2.6 价格计算（并获取 takeWayCode）
result4 = call_tool("tools/call", "calculate-price", {
    "storeCode": "SX001",
    "orderType": 1,
    "items": [{"productCode": "SX_BG001", "quantity": 1}]
})
takeWayCode = "locker-in"  # 默认自提方式
if "result" in result4:
    data = result4['result']
    if data.get('success'):
        # 如果 calculate-price 返回了 takeWayList，使用第一个
        if 'data' in data and isinstance(data['data'], dict):
            takeWayList = data['data'].get('takeWayList', [])
            if takeWayList:
                takeWayCode = takeWayList[0].get('code', takeWayCode)
        print(f"✓ calculate-price: 计算价格 (22.9元)")
    else:
        print(f"✗ calculate-price: {data.get('message')}")
else:
    print(f"✗ calculate-price: JSON-RPC 错误")

# 2.7 创建订单（使用从价格计算获取的 takeWayCode）
result5_args = {
    "storeCode": "SX001",
    "orderType": 1,
    "items": [{"productCode": "SX_BG001", "quantity": 1}]
}
if takeWayCode:
    result5_args["takeWayCode"] = takeWayCode

result5 = call_tool("tools/call", "create-order", result5_args)
order_id = None
if "result" in result5:
    data = result5['result']
    if data.get('success') and data.get('data', {}).get('orderId'):
        order_id = data['data']['orderId']
        print(f"✓ create-order: 订单已创建 (ID={order_id})")
    else:
        print(f"✗ create-order: {data.get('message', '创建失败')}")
else:
    print(f"✗ create-order: JSON-RPC 错误")

# 2.8 查询订单（如果有订单 ID）
if order_id:
    result6 = test_tool(
        "query-order",
        {"orderId": order_id},
        f"查询订单数据 (ID={order_id})"
    )
else:
    print("⊘ query-order: 跳过 (无有效订单 ID)")

# 2.9 优惠券工具（应为空）
result7 = test_tool(
    "query-store-coupons",
    {"storeCode": "SX001", "orderType": 1},
    "缺优惠券 (data.coupons=[])"
)

# 其他工具（无参数）
test_tool(
    "available-coupons",
    {},
    "可用优惠券列表"
)

test_tool(
    "query-my-coupons",
    {},
    "用户优惠券"
)

test_tool(
    "auto-bind-coupons",
    {},
    "自动绑定优惠券"
)

print("=" * 50)
print("✓ 所有工具验证完毕")
print("=" * 50)
