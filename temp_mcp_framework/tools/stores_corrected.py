"""
门店相关工具模块 - 修正版
根据麦当劳MCP真实文档对齐接口
"""

import json
import datetime
import uuid
from typing import Dict, Any, List, Optional
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
STORES_FILE = os.path.join(DATA_DIR, "stores.json")

def load_stores() -> List[Dict[str, Any]]:
    """加载门店数据"""
    try:
        with open(STORES_FILE, 'r', encoding='utf-8') as f:
            stores = json.load(f)
        return stores
    except FileNotFoundError:
        print(f"警告: 门店数据文件未找到: {STORES_FILE}")
        return []
    except json.JSONDecodeError as e:
        print(f"错误: 门店数据文件格式错误: {e}")
        return []

def query_nearby_stores(searchType: int = 1, beType: int = 1, city: str = None, keyword: str = None) -> Dict[str, Any]:
    """
    查询附近可用门店 - 修正版
    参数与麦当劳MCP的query-nearby-stores完全一致
    
    参数:
      searchType: 必填，1：查询收藏，2：按位置搜索，默认选中1
      beType: 必填，默认1，到店
      city: 城市，仅在searchType=2时必填
      keyword: 位置关键词，仅在searchType=2时必填
    
    返回:
      符合麦当劳MCP统一返回格式的结果
    """
    try:
        # 参数验证
        if searchType not in [1, 2]:
            return {
                "success": False,
                "code": 400,
                "message": "searchType参数错误，必须为1或2",
                "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "traceId": str(uuid.uuid4()),
                "data": None
            }
        
        if searchType == 2:
            if not city:
                return {
                    "success": False,
                    "code": 400,
                    "message": "searchType=2时city参数必填",
                    "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "traceId": str(uuid.uuid4()),
                    "data": None
                }
            if not keyword:
                return {
                    "success": False,
                    "code": 400,
                    "message": "searchType=2时keyword参数必填",
                    "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "traceId": str(uuid.uuid4()),
                    "data": None
                }
        
        # 加载门店数据
        stores = load_stores()
        if not stores:
            return {
                "success": False,
                "code": 500,
                "message": "门店数据加载失败",
                "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "traceId": str(uuid.uuid4()),
                "data": None
            }
        
        # 模拟搜索结果
        # 实际应根据city和keyword过滤，这里简单返回所有门店
        result_stores = []
        for store in stores:
            # 转换数据结构以匹配麦当劳MCP格式
            result_store = {
                "storeCode": store.get("storeCode", ""),
                "storeName": store.get("storeName", ""),
                "beCode": "",  # 虚拟数据，留空
                "address": store.get("address", ""),
                "distance": store.get("distanceKm", "1.5")  # 默认距离
            }
            result_stores.append(result_store)
        
        # 构建响应结构（与麦当劳MCP完全一致）
        response = {
            "success": True,
            "code": 200,
            "message": "请求成功",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": result_stores
        }
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "code": 500,
            "message": f"查询附近门店时发生错误: {str(e)}",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": None
        }

def query_store_coupons(storeCode: str, beCode: str = None, orderType: int = 1) -> Dict[str, Any]:
    """
    查询用户在当前门店可用券 - 修正版
    参数与麦当劳MCP的query-store-coupons完全一致
    
    参数:
      storeCode: 门店编码，必填
      beCode: BE编码
      orderType: 必填，到店：orderType=1，外送：orderType=2
    
    返回:
      符合麦当劳MCP统一返回格式的结果
    """
    try:
        if not storeCode:
            return {
                "success": False,
                "code": 400,
                "message": "storeCode参数必填",
                "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "traceId": str(uuid.uuid4()),
                "data": None
            }
        
        if orderType not in [1, 2]:
            return {
                "success": False,
                "code": 400,
                "message": "orderType参数错误，必须为1或2",
                "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "traceId": str(uuid.uuid4()),
                "data": None
            }
        
        # 模拟优惠券数据
        coupon_data = [
            {
                "title": "虚拟快餐店专享券",
                "couponId": "VIRTUAL001",
                "couponCode": "VIRTUAL001CODE",
                "tradeDateTime": f"{datetime.datetime.now().strftime('%Y-%m-%d')} 00:00:00-2026-12-31 23:59:59",
                "products": [
                    {
                        "productCode": "BG001",
                        "productName": "巨无霸汉堡"
                    }
                ]
            }
        ]
        
        response = {
            "success": True,
            "code": 200,
            "message": "请求成功",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": coupon_data
        }
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "code": 500,
            "message": f"查询门店优惠券时发生错误: {str(e)}",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": None
        }

def _register_tools(register_tool_func):
    """注册本模块的工具到MCP服务器"""
    
    # query-nearby-stores 工具的输入schema
    query_nearby_stores_schema = {
        "type": "object",
        "properties": {
            "searchType": {
                "type": "number",
                "description": "必填，1：查询收藏，2：按位置搜索，默认选中1",
                "default": 1,
                "enum": [1, 2]
            },
            "beType": {
                "type": "number",
                "description": "必填，默认1，到店",
                "default": 1
            },
            "city": {
                "type": "string",
                "description": "城市，仅在searchType=2时必填"
            },
            "keyword": {
                "type": "string",
                "description": "位置关键词，仅在searchType=2时必填"
            }
        },
        "required": ["searchType", "beType"]
    }
    
    # query-store-coupons 工具的输入schema
    query_store_coupons_schema = {
        "type": "object",
        "properties": {
            "storeCode": {
                "type": "string",
                "description": "门店编码，必填"
            },
            "beCode": {
                "type": "string",
                "description": "BE编码"
            },
            "orderType": {
                "type": "number",
                "description": "必填，到店：orderType=1，外送：orderType=2",
                "default": 1,
                "enum": [1, 2]
            }
        },
        "required": ["storeCode", "orderType"]
    }
    
    register_tool_func(
        name="query-nearby-stores",
        description="查询用户提供地址附近的麦当劳餐厅。当用户希望想要到店取餐、堂食或希望寻找麦当劳餐厅时可以使用该工具查找位置附近的麦当劳门店",
        input_schema=query_nearby_stores_schema,
        handler=query_nearby_stores
    )
    
    register_tool_func(
        name="query-store-coupons",
        description="查询用户在当前门店下可使用的优惠券列表，用于点餐时选择可用优惠",
        input_schema=query_store_coupons_schema,
        handler=query_store_coupons
    )
    
    print("[OK] 注册门店工具: query-nearby-stores, query-store-coupons")

if __name__ == "__main__":
    # 测试代码
    print("测试 stores_corrected.py 工具模块...")
    
    print("1. 测试 query-nearby-stores (searchType=1):")
    result = query_nearby_stores(searchType=1, beType=1)
    print(f"成功: {result['success']}")
    print(f"状态码: {result['code']}")
    print(f"消息: {result['message']}")
    print(f"门店数量: {len(result['data']) if result['data'] else 0}")
    
    print("\n2. 测试 query-store-coupons:")
    result = query_store_coupons(storeCode="VS001", orderType=1)
    print(f"成功: {result['success']}")
    print(f"状态码: {result['code']}")
    print(f"优惠券数量: {len(result['data']) if result['data'] else 0}")