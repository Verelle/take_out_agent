"""
菜单相关工具模块 - 修正版
根据麦当劳MCP真实文档对齐接口
实现 query-meals 和 query-meal-detail 工具
"""

import json
import datetime
import uuid
from typing import Dict, Any, List, Optional
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MENU_FILE = os.path.join(DATA_DIR, "menu.json")

def load_menu_data() -> List[Dict[str, Any]]:
    """加载菜单数据"""
    try:
        with open(MENU_FILE, 'r', encoding='utf-8') as f:
            menu_data = json.load(f)
        return menu_data
    except FileNotFoundError:
        print(f"警告: 菜单数据文件未找到: {MENU_FILE}")
        return []
    except json.JSONDecodeError as e:
        print(f"错误: 菜单数据文件格式错误: {e}")
        return []

def find_store_menu(store_code: str) -> Optional[Dict[str, Any]]:
    """根据门店代码查找菜单"""
    menu_data = load_menu_data()
    for store_menu in menu_data:
        if store_menu.get("storeCode") == store_code:
            return store_menu
    return None

def find_meal_detail(code: str, store_code: str = None) -> Optional[Dict[str, Any]]:
    """根据餐品编码查找餐品详情"""
    menu_data = load_menu_data()
    
    for store_menu in menu_data:
        # 如果指定了门店代码，只搜索该门店
        if store_code and store_code != store_menu.get("storeCode"):
            continue
            
        for category in store_menu.get("categories", []):
            for item in category.get("items", []):
                if item.get("mealCode") == code:
                    return item
    return None

def query_meals(storeCode: str, beCode: str = None, orderType: int = 1) -> Dict[str, Any]:
    """
    查询当前可售卖的餐品列表 - 修正版
    参数与麦当劳MCP的query-meals完全一致
    
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
        
        store_menu = find_store_menu(storeCode)
        if not store_menu:
            return {
                "success": False,
                "code": 404,
                "message": f"未找到门店 '{storeCode}' 的菜单",
                "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "traceId": str(uuid.uuid4()),
                "data": None
            }
        
        # 转换数据结构以匹配麦当劳MCP格式
        categories = []
        meals = {}
        
        for category in store_menu.get("categories", []):
            category_id = category.get("categoryId", "")
            category_name = category.get("categoryName", "")
            
            # 转换分类结构
            mcd_category = {
                "name": category_name,
                "meals": [],
                "daypart": 8  # 默认值，表示全天
            }
            
            for item in category.get("items", []):
                meal_code = item.get("mealCode", "")
                meal_name = item.get("mealName", "")
                
                # 添加到分类的餐品列表
                mcd_category["meals"].append({
                    "code": meal_code,
                    "tags": item.get("tags", [])
                })
                
                # 添加到餐品详情映射
                meals[meal_code] = {
                    "name": meal_name,
                    "currentPrice": str(item.get("price", 0))
                }
            
            categories.append(mcd_category)
        
        # 构建响应结构（与麦当劳MCP完全一致）
        response = {
            "success": True,
            "code": 200,
            "message": "请求成功",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": {
                "categories": categories,
                "meals": meals
            }
        }
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "code": 500,
            "message": f"查询菜单时发生错误: {str(e)}",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": None
        }

def query_meal_detail(code: str, storeCode: str = None, beCode: str = None, orderType: int = 1) -> Dict[str, Any]:
    """
    查询餐品详情 - 修正版
    参数与麦当劳MCP的query-meal-detail完全一致
    
    参数:
      code: 餐品编码，必填
      storeCode: 门店 code
      beCode: BE编码
      orderType: 必填，到店：orderType=1，外送：orderType=2
    
    返回:
      符合麦当劳MCP统一返回格式的结果
    """
    try:
        if not code:
            return {
                "success": False,
                "code": 400,
                "message": "code参数必填",
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
        
        meal_item = find_meal_detail(code, storeCode)
        if not meal_item:
            error_msg = f"未找到餐品 '{code}'"
            if storeCode:
                error_msg += f"（门店: {storeCode}）"
            return {
                "success": False,
                "code": 404,
                "message": error_msg,
                "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "traceId": str(uuid.uuid4()),
                "data": None
            }
        
        # 构建响应结构（与麦当劳MCP完全一致）
        # 注意：当前版本(v1.0.3)暂不支持更换套餐内的单品
        response = {
            "success": True,
            "code": 200,
            "message": "请求成功",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": {
                "code": code,
                "price": str(meal_item.get("price", 0)),
                "rounds": [
                    {
                        "id": 1,
                        "name": "主餐",
                        "quantity": 1,
                        "maxQuantity": 1,
                        "minQuantity": 1,
                        "choices": [
                            {
                                "code": "1000",
                                "name": meal_item.get("mealName", ""),
                                "quantity": 1,
                                "maxQuantity": -1  # -1表示无限制
                            }
                        ]
                    }
                ]
            }
        }
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "code": 500,
            "message": f"查询餐品详情时发生错误: {str(e)}",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": None
        }

def _register_tools(register_tool_func):
    """注册本模块的工具到MCP服务器"""
    
    # query-meals 工具的输入schema
    query_meals_schema = {
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
    
    # query-meal-detail 工具的输入schema
    query_meal_detail_schema = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "餐品编码，必填"
            },
            "storeCode": {
                "type": "string",
                "description": "门店 code"
            },
            "beCode": {
                "type": "string",
                "description": "BE编码"
            },
            "orderType": {
                "type": "number",
                "description": "必填",
                "enum": [1, 2]
            }
        },
        "required": ["code", "orderType"]
    }
    
    register_tool_func(
        name="query-meals",
        description="查询当前门店可售餐品列表。当用户希望获取门店菜单或者点单时，可以调用这个工具获取当前门店可售的餐品。",
        input_schema=query_meals_schema,
        handler=query_meals
    )
    
    register_tool_func(
        name="query-meal-detail",
        description="根据餐品列表中返回的餐品编码，可以查看套餐的组成等信息。当用户需要查看餐品详情时使用此工具。",
        input_schema=query_meal_detail_schema,
        handler=query_meal_detail
    )
    
    print("[OK] 注册菜单工具: query-meals, query-meal-detail")

if __name__ == "__main__":
    # 测试代码
    print("测试 menu_corrected.py 工具模块...")
    
    print("1. 测试 query-meals (storeCode=VS001):")
    result = query_meals(storeCode="VS001", orderType=1)
    print(f"成功: {result['success']}")
    print(f"状态码: {result['code']}")
    print(f"消息: {result['message']}")
    if result["success"]:
        data = result["data"]
        print(f"分类数: {len(data['categories'])}")
        print(f"餐品数: {len(data['meals'])}")
    
    print("\n2. 测试 query-meal-detail (code=BG001):")
