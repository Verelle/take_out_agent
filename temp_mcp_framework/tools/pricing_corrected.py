"""
价格计算工具模块 - 修正版
根据麦当劳MCP真实文档对齐接口
实现 calculate-price 工具
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

def find_meal_price(meal_code: str, store_code: str = None) -> float:
    """根据餐品编码查找价格"""
    menu_data = load_menu_data()
    
    for store_menu in menu_data:
        # 如果指定了门店代码，只搜索该门店
        if store_code and store_code != store_menu.get("storeCode"):
            continue
            
        for category in store_menu.get("categories", []):
            for item in category.get("items", []):
                if item.get("mealCode") == meal_code:
                    return float(item.get("price", 0))
    
    # 找不到则返回默认价格
    return 15.0  # 默认价格

def find_meal_name(meal_code: str, store_code: str = None) -> str:
    """根据餐品编码查找餐品名称"""
    menu_data = load_menu_data()
    for store_menu in menu_data:
        if store_code and store_code != store_menu.get("storeCode"):
            continue
        for category in store_menu.get("categories", []):
            for item in category.get("items", []):
                if item.get("mealCode") == meal_code:
                    return item.get("mealName", meal_code)
    return meal_code

def calculate_price(
    storeCode: str,
    beCode: str = None,
    orderType: int = 1,
    items: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    商品价格计算 - 修正版
    参数与麦当劳MCP的calculate-price完全一致
    
    参数:
      storeCode: 门店编码，必填
      beCode: BE编码
      orderType: 必填，到店：orderType=1，外送（麦乐送&团餐）：orderType=2
      items: 商品列表（数组）
    
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
        
        if not items or len(items) == 0:
            return {
                "success": False,
                "code": 400,
                "message": "items参数不能为空",
                "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "traceId": str(uuid.uuid4()),
                "data": None
            }
        
        # 验证items结构
        for i, item in enumerate(items):
            if "productCode" not in item:
                return {
                    "success": False,
                    "code": 400,
                    "message": f"items[{i}]缺少productCode字段",
                    "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "traceId": str(uuid.uuid4()),
                    "data": None
                }
            if "quantity" not in item:
                return {
                    "success": False,
                    "code": 400,
                    "message": f"items[{i}]缺少quantity字段",
                    "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "traceId": str(uuid.uuid4()),
                    "data": None
                }
        
        # 计算价格（单位：元）
        product_original_price = 0.0
        product_price = 0.0
        discount = 0.0
        product_list = []

        for item in items:
            product_code = item["productCode"]
            quantity = item["quantity"]
            coupon_id = item.get("couponId")
            coupon_code = item.get("couponCode")

            unit_price = find_meal_price(product_code, storeCode)  # 返回元（float）
            original_subtotal = unit_price * quantity

            # 优惠逻辑：有券打8折
            subtotal = original_subtotal
            if coupon_id and coupon_code:
                discount_amount = original_subtotal * 0.2
                subtotal = original_subtotal - discount_amount
                discount += discount_amount

            product_original_price += original_subtotal
            product_price += subtotal

            product_list.append({
                "productCode": product_code,
                "productName": find_meal_name(product_code, storeCode),
                "quantity": quantity,
                "originalSubtotal": round(original_subtotal, 2),
                "subtotal": round(subtotal, 2)
            })
        
        # 配送费（元）
        delivery_original_price = 6.0 if orderType == 2 else 0.0
        delivery_price = delivery_original_price
        
        original_price = product_original_price + delivery_original_price
        price = product_price + delivery_price
        
        # 构建响应结构（与麦当劳MCP完全一致）
        response = {
            "success": True,
            "code": 200,
            "message": "请求成功",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": {
                "productOriginalPrice": round(product_original_price, 2),
                "productPrice": round(product_price, 2),
                "deliveryOriginalPrice": round(delivery_original_price, 2),
                "deliveryPrice": round(delivery_price, 2),
                "originalPrice": round(original_price, 2),
                "discount": round(discount, 2),
                "price": round(price, 2),
                "productList": product_list,
                "takeWayList": [{"code": "locker-in", "name": "自取"}],
                "mealAssistanceList": []
            }
        }
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "code": 500,
            "message": f"价格计算时发生错误: {str(e)}",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": None
        }

def _register_tools(register_tool_func):
    """注册本模块的工具到MCP服务器"""
    
    # calculate-price 工具的输入schema
    calculate_price_schema = {
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
                "description": "必填，到店：orderType=1，外送（麦乐送&团餐）：orderType=2",
                "default": 1,
                "enum": [1, 2]
            },
            "items": {
                "type": "array",
                "description": "商品列表（数组）",
                "items": {
                    "type": "object",
                    "properties": {
                        "productCode": {
                            "type": "string",
                            "description": "餐品编码，必填（如果用户使用优惠券，则productCode为券商品code）"
                        },
                        "quantity": {
                            "type": "number",
                            "description": "商品数量，必填"
                        },
                        "couponId": {
                            "type": "string",
                            "description": "优惠券ID，当用户要使用优惠券时必填"
                        },
                        "couponCode": {
                            "type": "string",
                            "description": "优惠券编码，当用户要使用优惠券时必填"
                        }
                    },
                    "required": ["productCode", "quantity"]
                }
            }
        },
        "required": ["storeCode", "orderType", "items"]
    }
    
    register_tool_func(
        name="calculate-price",
        description="计算用户购买商品及优惠价格。当用户询问商品或商品组合的价格时，可以使用此工具获取订单价格信息。",
        input_schema=calculate_price_schema,
        handler=calculate_price
    )
    
    print("[OK] 注册价格工具: calculate-price")

if __name__ == "__main__":
    # 测试代码
    print("测试 pricing_corrected.py 工具模块...")
    
    print("1. 测试 calculate-price (到店场景):")
    test_items = [
        {"productCode": "SX_BG001", "quantity": 2},
        {"productCode": "SX_FR001", "quantity": 1}
    ]
    result = calculate_price(storeCode="SX001", orderType=1, items=test_items)
    print(f"成功: {result['success']}")
    print(f"状态码: {result['code']}")
    print(f"消息: {result['message']}")
    if result["success"]:
        data = result["data"]
        print(f"商品原价: {data['productOriginalPrice']:.2f}元")
        print(f"商品实价: {data['productPrice']:.2f}元")
        print(f"配送费: {data['deliveryPrice']:.2f}元")
        print(f"总价: {data['price']:.2f}元")
    
    print("\n2. 测试 calculate-price (外送场景，带优惠券):")
    test_items_with_coupon = [
        {"productCode": "SX_BG001", "quantity": 1, "couponId": "COUPON001", "couponCode": "CODE001"}
    ]
    result = calculate_price(storeCode="SX001", orderType=2, items=test_items_with_coupon)
    print(f"成功: {result['success']}")
    if result["success"]:
        data = result["data"]
        print(f"折扣金额: {data['discount']:.2f}元")
        print(f"最终总价: {data['price']:.2f}元")