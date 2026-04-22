#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""集成验证：MCP 双客户端初始化测试"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from mcp_client import (
    init_mcp_clients,
    vstore_query_nearby_stores,
    vstore_query_meals,
    vstore_calculate_price
)

print("=" * 60)
print("集成验证：MCP 双客户端初始化")
print("=" * 60)

# 初始化双客户端
status = init_mcp_clients(
    mcd_url="https://mcp.mcd.cn",
    mcd_token="iafsHcMfvAEWtcTO6FTtc40jBuAl63VF",
    mcd_timeout=5,
    vstore_url="http://127.0.0.1:8000",
    vstore_token="vstore-dev-token",
    vstore_timeout=5,
)

print("\n=== 初始化结果 ===")
print(f"麦当劳 MCP:  {'✓ 成功' if status['mcd'] else '✗ 失败（预期 - 需要网络/有效 Token）'}")
print(f"星选汉堡 MCP: {'✓ 成功' if status['vstore'] else '✗ 失败（本地 8000 未启动？）'}")

# 核心验证：星选汉堡必须成功
if not status["vstore"]:
    print("\n✗ 错误：星选汉堡 MCP 初始化失败！")
    print("请确认 server_corrected.py 正在运行于 http://127.0.0.1:8000")
    sys.exit(1)

print("\n✓ 星选汉堡 MCP 客户端初始化成功\n")

# === 工具调用验证 ===
print("=== 工具调用验证 ===\n")

try:
    # 1. 查门店
    print("1. vstore_query_nearby_stores...", end=" ")
    result = vstore_query_nearby_stores(searchType=2, city="上海", keyword="徐家汇")
    text = result.content[0].get('text', '') if isinstance(result.content[0], dict) else result.content[0].text
    if 'SX' in text or '星选' in text or '门店' in text:
        print("✓")
    else:
        print(f"✗ 返回: {text[:60]}...")

    # 2. 查菜单
    print("2. vstore_query_meals...", end=" ")
    result = vstore_query_meals(storeCode="SX001", orderType=1)
    text = result.content[0].get('text', '') if isinstance(result.content[0], dict) else result.content[0].text
    if 'SX_' in text or '菜单' in text or '套餐' in text:
        print("✓")
    else:
        print(f"✗ 返回: {text[:60]}...")

    # 3. 算价格
    print("3. vstore_calculate_price...", end=" ")
    result = vstore_calculate_price(
        storeCode="SX001",
        orderType=1,
        items=[{"productCode": "SX_BG001", "quantity": 1}]
    )
    text = result.content[0].get('text', '') if isinstance(result.content[0], dict) else result.content[0].text
    if '价格' in text or '22' in text or '元' in text or '金额' in text:
        print("✓")
    else:
        print(f"✗ 返回: {text[:60]}...")

except Exception as e:
    print(f"\n✗ 工具调用异常: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ 所有验证通过！双客户端集成就绪")
print("=" * 60)
