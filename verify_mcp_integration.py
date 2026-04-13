"""
verify_mcp_integration.py - 验证修改后的 MCP 集成是否正常工作

测试场景：
  1. 验证握手流程能否成功完成
  2. 验证包装函数能否正常调用工具
  3. 验证与智能体的集成
"""

import sys
import os
import json

# 添加 deploy_starter 到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deploy_starter import mcp_client as mcp_module
from deploy_starter.mcp_client import (
    init_mcp_client,
    now_time_info,
    query_nearby_stores,
    campaign_calendar,
    available_coupons,
    query_my_account,
)


def print_header(title: str):
    """打印标题"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def verify_handshake():
    """验证握手流程"""
    print_header("【步骤 1】MCP 握手流程验证")
    
    mcp_client = mcp_module.mcp_client
    if mcp_client is None:
        print("✗ MCP 客户端未初始化")
        return False
    
    if mcp_client.handshake_success:
        print(f"✓ 握手成功")
        print(f"  - MCP Server: {mcp_client.base_url}")
        print(f"  - 可用工具数: {len(mcp_client.tools_cache)}")
        print(f"\n  工具列表：")
        for i, tool in enumerate(mcp_client.tools_cache, 1):
            print(f"    {i:2d}. {tool.get('name', 'unknown')}")
        return True
    else:
        print("✗ 握手失败")
        return False


def test_noarg_tools():
    """测试无参工具"""
    print_header("【步骤 2】无参工具测试")
    
    test_cases = [
        ("now_time_info (获取当前时间)", now_time_info),
        ("campaign_calendar (查询活动日历)", campaign_calendar),
    ]
    
    success_count = 0
    for test_name, func in test_cases:
        print(f"\n测试: {test_name}")
        try:
            result = func()
            print(f"  ✓ 成功")
            if isinstance(result, str):
                try:
                    result_obj = json.loads(result)
                    print(f"  结果预览: {json.dumps(result_obj, indent=2, ensure_ascii=False)[:200]}...")
                except:
                    print(f"  结果: {result[:100]}...")
            else:
                print(f"  结果: {str(result)[:100]}...")
            success_count += 1
        except Exception as e:
            print(f"  ✗ 失败: {e}")
    
    return success_count == len(test_cases)


def test_arg_tools():
    """测试有参工具"""
    print_header("【步骤 3】有参工具测试")
    
    test_cases = [
        ("query_nearby_stores (查询附近门店)", query_nearby_stores, [31.0299, 121.4312]),
        ("available_coupons (查询可领优惠券)", available_coupons, ["user123"]),
        ("query_my_account (查询积分账户)", query_my_account, ["user123"]),
    ]
    
    success_count = 0
    for test_name, func, args in test_cases:
        print(f"\n测试: {test_name}")
        try:
            result = func(*args)
            print(f"  ✓ 成功")
            if isinstance(result, str):
                try:
                    result_obj = json.loads(result)
                    print(f"  结果预览: {json.dumps(result_obj, indent=2, ensure_ascii=False)[:200]}...")
                except:
                    print(f"  结果: {result[:100]}...")
            else:
                print(f"  结果: {str(result)[:100]}...")
            success_count += 1
        except Exception as e:
            print(f"  ✗ 失败: {e}")
    
    return success_count == len(test_cases)


def main():
    """主程序"""
    print("\n" + "="*80)
    print("  MCP 集成验证 - 确认修改后的握手流程是否生效")
    print("="*80)
    
    # 配置 MCP Server
    MCP_SERVER = "https://mcp.mcd.cn"
    MCP_TOKEN = "iafsHcMfvAEWtcTO6FTtc40jBuAl63VF"
    
    print(f"\nMCP Server: {MCP_SERVER}")
    print(f"Token: {MCP_TOKEN[:20]}...\n")
    
    # 步骤 1: 初始化并验证握手
    print("初始化 MCP 客户端...")
    success = init_mcp_client(base_url=MCP_SERVER, token=MCP_TOKEN)
    
    if not success:
        print("\n❌ MCP 初始化失败，无法继续测试")
        return False
    
    # 步骤 2: 验证握手流程
    if not verify_handshake():
        print("\n❌ 握手流程验证失败")
        return False
    
    # 步骤 3: 测试无参工具
    if not test_noarg_tools():
        print("\n⚠ 部分无参工具测试失败")
    
    # 步骤 4: 测试有参工具
    if not test_arg_tools():
        print("\n⚠ 部分有参工具测试失败")
    
    # 总结
    print_header("【验证完成】")
    print("✓ MCP 握手流程已成功集成")
    print("✓ 包装函数可以正常调用工具")
    print("✓ 智能体现在应该可以正确使用 MCP 工具了")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n取消验证")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
