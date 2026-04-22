"""
订单相关工具模块 - 修正版
根据麦当劳MCP真实文档对齐接口
实现 create-order 和 query-order 工具
使用内存存储订单状态（演示场景足够）
"""

import uuid
import datetime
import json
from typing import Dict, Any, List, Optional
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
STORES_FILE = os.path.join(DATA_DIR, "stores.json")

# 将 tools 目录加入路径，以便 import pricing_corrected
sys.path.insert(0, os.path.join(BASE_DIR, "tools"))
from pricing_corrected import find_meal_price, find_meal_name

def find_store_name(store_code: str) -> str:
    """根据门店编码从 stores.json 查找门店名称"""
    try:
        with open(STORES_FILE, 'r', encoding='utf-8') as f:
            stores = json.load(f)
        for store in stores:
            if store.get("storeCode") == store_code:
                return store.get("storeName", f"星选汉堡({store_code})")
    except Exception:
        pass
    return f"星选汉堡({store_code})"

# 内存订单存储
orders_db = {}

# 订单状态枚举（与麦当劳MCP对齐）
ORDER_STATUS = {
    "PENDING": "待支付",        # 待支付
    "PAID": "已支付",           # 已支付
    "PREPARING": "制作中",      # 制作中
    "READY": "待取餐",          # 待取餐/配送
    "COMPLETED": "已完成",      # 已完成
    "CANCELLED": "已取消"       # 已取消
}

def generate_order_id() -> str:
    """生成订单ID"""
    return f"VS{datetime.datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

def generate_pay_id() -> str:
    """生成支付ID"""
    return str(uuid.uuid4()).replace("-", "")

def create_order(
    storeCode: str = None,
    beCode: str = None,
    addressId: str = None,
    takeWayCode: str = None,
    orderType: int = 1,
    items: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    创建订单 - 修正版
    参数与麦当劳MCP的create-order完全一致
    
    参数:
      storeCode: 门店编码
      beCode: BE编码
      addressId: 外送场景下必填
      takeWayCode: 到店场景下必填，需要从 calculate-price 的价格计算工具中获取
      orderType: 必填，到店：orderType=1，外送（麦乐送&团餐）：orderType=2
      items: 商品列表（数组）
    
    返回:
      符合麦当劳MCP统一返回格式的结果
    """
    try:
        # 参数验证
        if orderType not in [1, 2]:
            return {
                "success": False,
                "code": 400,
                "message": "orderType参数错误，必须为1或2",
                "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "traceId": str(uuid.uuid4()),
                "data": None
            }
        
        if orderType == 2 and not addressId:
            return {
                "success": False,
                "code": 400,
                "message": "外送场景下addressId参数必填",
                "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "traceId": str(uuid.uuid4()),
                "data": None
            }
        
        if orderType == 1 and not takeWayCode:
            takeWayCode = "locker-in"  # 默认自取，避免 Agent 因拿不到 takeWayCode 而下单失败
        
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
        
        # 生成订单信息
        order_id = generate_order_id()
        pay_id = generate_pay_id()
        now = datetime.datetime.now()
        
        # 构建订单详情（简化版）
        order_product_list = []
        total_amount = 0
        for item in items:
            product_code = item["productCode"]
            quantity = item["quantity"]
            
            unit_price = find_meal_price(product_code, storeCode)  # 从菜单读取（元）
            price = unit_price * quantity
            
            order_product_list.append({
                "productName": find_meal_name(product_code, storeCode),
                "quantity": quantity,
                "price": f"{price:.2f}",
                "comboItemList": [
                    {"itemName": find_meal_name(product_code, storeCode), "itemQuantity": quantity}
                ]
            })
            total_amount += price
        
        # 配送信息
        delivery_info = {
            "deliveryType": "立即送出",
            "deliveryAddress": "虚拟配送地址",
            "addressDetail": "xxx号房间",
            "customerNickname": "虚拟用户",
            "mobilePhone": "138****8888",
            "expectDeliveryTime": f"{now.hour + 1}:00"  # 1小时后
        }
        
        # 创建订单对象
        order = {
            "orderId": order_id,
            "orderStatus": ORDER_STATUS["PENDING"],
            "storeName": find_store_name(storeCode) if storeCode else "星选汉堡",
            "storeAddress": "上海市虚拟地址",
            "orderProductList": order_product_list,
            "totalAmount": f"{total_amount:.2f}",
            "realTotalAmount": f"{total_amount:.2f}",
            "totalDiscountAmount": "0",
            "couponList": [],
            "deliveryInfo": delivery_info,
            "createTime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "deliveryPrice": "6.00" if orderType == 2 else "0.00",
            "realDeliveryPrice": "6.00" if orderType == 2 else "0.00",
            "productPrice": f"{total_amount:.2f}",
            "takeWay": takeWayCode if orderType == 1 else "",
            "pickupCode": "",
            "lockerCode": "",
            "mealAssistance": {
                "code": "",
                "name": "",
                "items": [{"name": ""}]
            }
        }
        
        # 存储订单
        orders_db[order_id] = order
        
        # 构建响应结构（与麦当劳MCP完全一致）
        response = {
            "success": True,
            "code": 200,
            "message": "请求成功",
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": {
                "orderId": order_id,
                "payId": pay_id,
                "payH5Url": f"https://virtual-mcp.com/pay?orderId={order_id}&payId={pay_id}",
                "orderDetail": order
            }
        }
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "code": 500,
            "message": f"创建订单时发生错误: {str(e)}",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": None
        }

def query_order(orderId: str) -> Dict[str, Any]:
    """
    查询订单详情 - 修正版
    参数与麦当劳MCP的query-order完全一致
    
    参数:
      orderId: 订单号，必填
    
    返回:
      符合麦当劳MCP统一返回格式的结果
    """
    try:
        if not orderId:
            return {
                "success": False,
                "code": 400,
                "message": "orderId参数必填",
                "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "traceId": str(uuid.uuid4()),
                "data": None
            }
        
        # 查找订单
        order = orders_db.get(orderId)
        if not order:
            return {
                "success": False,
                "code": 404,
                "message": f"未找到订单 '{orderId}'",
                "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "traceId": str(uuid.uuid4()),
                "data": None
            }
        
        # 构建响应结构（与麦当劳MCP完全一致）
        response = {
            "success": True,
            "code": 200,
            "message": "请求成功",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": order
        }
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "code": 500,
            "message": f"查询订单时发生错误: {str(e)}",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": None
        }

def _register_tools(register_tool_func):
    """注册本模块的工具到MCP服务器"""
    
    # create-order 工具的输入schema
    create_order_schema = {
        "type": "object",
        "properties": {
            "storeCode": {
                "type": "string",
                "description": "门店编码"
            },
            "beCode": {
                "type": "string",
                "description": "BE编码"
            },
            "addressId": {
                "type": "string",
                "description": "外送场景下必填"
            },
            "takeWayCode": {
                "type": "string",
                "description": "到店场景下必填，需要从 calculate-price 的价格计算工具中获取"
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
                            "description": "优惠券ID，当用户使用优惠券时必填"
                        },
                        "couponCode": {
                            "type": "string",
                            "description": "优惠券编码，当用户使用优惠券时必填"
                        }
                    },
                    "required": ["productCode", "quantity"]
                }
            }
        },
        "required": ["orderType", "items"]
    }
    
    # query-order 工具的输入schema
    query_order_schema = {
        "type": "object",
        "properties": {
            "orderId": {
                "type": "string",
                "description": "订单号，必填"
            }
        },
        "required": ["orderId"]
    }
    
    register_tool_func(
        name="create-order",
        description="创建订单。当用户希望下单/购买选中商品时可以使用该工具进行下单。",
        input_schema=create_order_schema,
        handler=create_order
    )
    
    register_tool_func(
        name="query-order",
        description="查询订单详情。当用户希望查询订单状态、订单进度等信息时，可以使用该工具获取。",
        input_schema=query_order_schema,
        handler=query_order
    )
    
    print("[OK] 注册订单工具: create-order, query-order")

if __name__ == "__main__":
    # 测试代码
    print("测试 orders_corrected.py 工具模块...")
    
    print("1. 测试 create-order (到店场景):")
    test_items = [
        {"productCode": "BG001", "quantity": 1}
    ]
    result = create_order(
        storeCode="VS001",
        takeWayCode="locker-in",
        orderType=1,
        items=test_items
    )
    print(f"成功: {result['success']}")
    print(f"状态码: {result['code']}")
    print(f"消息: {result['message']}")
    if result["success"]:
        data = result["data"]
        print(f"订单ID: {data['orderId']}")
        print(f"支付链接: {data['payH5Url']}")
        order_id = data["orderId"]
    
    print("\n2. 测试 query-order:")
    if result["success"]:
        result = query_order(orderId=order_id)
        print(f"成功: {result['success']}")
        if result["success"]:
            print(f"订单状态: {result['data']['orderStatus']}")
            print(f"订单金额: {result['data']['totalAmount']}元")