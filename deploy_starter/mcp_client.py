"""
mcp_client.py - 麦当劳 MCP Server 客户端封装

负责与远程 MCP Server 通信，提供工具调用接口。
支持通用的 MCP 工具调用，以及针对常见业务场景的便利方法。
"""

import os
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class McpClient:
    """
    麦当劳 MCP Server 客户端。

    初始化参数：
      - base_url: MCP Server 地址（如 https://api.mcd.example.com）
      - token: 认证 token
      - timeout: 请求超时时间（秒）
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _build_headers(self) -> Dict[str, str]:
        """构建请求 header，包含认证信息。"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    def call_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        通用工具调用方法。

        参数：
          - tool_name: MCP 工具名称（如 "query-meals"）
          - payload: 工具输入参数（字典）

        返回：
          - 工具执行结果（JSON 对象）

        异常：
          - requests.RequestException: 网络错误
          - ValueError: 服务端返回错误
        """
        url = f"{self.base_url}/tools/{tool_name}"
        try:
            response = requests.post(
                url,
                headers=self._build_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()
            logger.debug(f"MCP tool '{tool_name}' called successfully: {result}")
            return result
        except requests.RequestException as e:
            logger.error(f"MCP tool '{tool_name}' request failed: {e}")
            raise ValueError(f"麦当劳 MCP 调用失败：{str(e)}")


# ────────────────────────────────────────────────────────────────
# MCP 工具包装函数
# 每个函数对应一个 MCP 工具，AgentScope 可以直接注册这些函数
# ────────────────────────────────────────────────────────────────


def list_nutrition_foods(food_name: str = "") -> str:
    """
    列出麦当劳常见餐品的营养信息。

    参数：
      food_name: 餐品名称（可选，用于过滤）

    返回：
      餐品营养信息列表（JSON 字符串）
    """
    payload = {}
    if food_name:
        payload["foodName"] = food_name
    result = mcp_client.call_tool("list-nutrition-foods", payload)
    return str(result)


def query_nearby_stores(latitude: float, longitude: float) -> str:
    """
    查询用户位置附近的麦当劳门店。

    参数：
      latitude: 纬度
      longitude: 经度

    返回：
      附近门店列表（JSON 字符串）
    """
    payload = {
        "latitude": latitude,
        "longitude": longitude,
    }
    result = mcp_client.call_tool("query-nearby-stores", payload)
    return str(result)


def delivery_query_addresses(user_id: str) -> str:
    """
    查询用户已保存的配送地址列表。

    参数：
      user_id: 用户 ID

    返回：
      地址列表及对应门店信息（JSON 字符串）
    """
    payload = {"userId": user_id}
    result = mcp_client.call_tool("delivery-query-addresses", payload)
    return str(result)


def delivery_create_address(
    user_id: str,
    address: str,
    latitude: float = None,
    longitude: float = None,
) -> str:
    """
    为用户创建新的配送地址。

    参数：
      user_id: 用户 ID
      address: 地址文本
      latitude: 纬度（可选）
      longitude: 经度（可选）

    返回：
      新创建的地址信息（JSON 字符串）
    """
    payload = {
        "userId": user_id,
        "address": address,
    }
    if latitude is not None:
        payload["latitude"] = latitude
    if longitude is not None:
        payload["longitude"] = longitude
    result = mcp_client.call_tool("delivery-create-address", payload)
    return str(result)


def query_store_coupons(store_code: str, user_id: str) -> str:
    """
    查询用户在指定门店可使用的优惠券。

    参数：
      store_code: 门店代码
      user_id: 用户 ID

    返回：
      可用优惠券列表（JSON 字符串）
    """
    payload = {
        "storeCode": store_code,
        "userId": user_id,
    }
    result = mcp_client.call_tool("query-store-coupons", payload)
    return str(result)


def query_meals(store_code: str) -> str:
    """
    查询指定门店当前可售卖的餐品菜单。

    参数：
      store_code: 门店代码

    返回：
      菜单列表（包含分类、餐品编码、标签等）（JSON 字符串）
    """
    payload = {"storeCode": store_code}
    result = mcp_client.call_tool("query-meals", payload)
    return str(result)


def query_meal_detail(meal_code: str, store_code: str = None) -> str:
    """
    查询餐品的详细信息（如套餐组成、默认选择等）。

    参数：
      meal_code: 餐品编码
      store_code: 门店代码（可选）

    返回：
      餐品详情（JSON 字符串）
    """
    payload = {"mealCode": meal_code}
    if store_code:
        payload["storeCode"] = store_code
    result = mcp_client.call_tool("query-meal-detail", payload)
    return str(result)


def calculate_price(
    store_code: str,
    items: list,
    coupon_ids: list = None,
) -> str:
    """
    计算商品的价格，包括商品金额、配送费、优惠金额等。

    参数：
      store_code: 门店代码
      items: 商品列表，每个商品格式为 {"code": "...", "quantity": ...}
      coupon_ids: 优惠券 ID 列表（可选）

    返回：
      价格计算结果（包含总价、优惠、配送费等）（JSON 字符串）
    """
    payload = {
        "storeCode": store_code,
        "items": items,
    }
    if coupon_ids:
        payload["couponIds"] = coupon_ids
    result = mcp_client.call_tool("calculate-price", payload)
    return str(result)


def create_order(
    store_code: str,
    be_code: str,
    user_id: str,
    items: list,
    dine_in_type: str = "DELIVERY",
    coupon_ids: list = None,
    address_id: str = None,
) -> str:
    """
    创建订单。

    参数：
      store_code: 门店代码
      be_code: 门店 BE 代码
      user_id: 用户 ID
      items: 订单商品列表
      dine_in_type: 就餐方式（DELIVERY = 外送，PICKUP = 自取，DINE_IN = 堂食）
      coupon_ids: 优惠券 ID 列表（可选）
      address_id: 配送地址 ID（外送时必需）（可选）

    返回：
      订单详情及支付链接（JSON 字符串）
    """
    payload = {
        "storeCode": store_code,
        "beCode": be_code,
        "userId": user_id,
        "items": items,
        "dineInType": dine_in_type,
    }
    if coupon_ids:
        payload["couponIds"] = coupon_ids
    if address_id:
        payload["addressId"] = address_id
    result = mcp_client.call_tool("create-order", payload)
    return str(result)


def query_order(order_id: str, user_id: str) -> str:
    """
    查询订单详情（包括订单状态、内容、配送信息等）。

    参数：
      order_id: 订单 ID
      user_id: 用户 ID

    返回：
      订单信息（JSON 字符串）
    """
    payload = {
        "orderId": order_id,
        "userId": user_id,
    }
    result = mcp_client.call_tool("query-order", payload)
    return str(result)


def campaign_calendar() -> str:
    """
    查询麦当劳中国当月的营销活动日历。

    返回：
      活动日历信息（包括进行中、往期和未来日期的活动）（JSON 字符串）
    """
    payload = {}
    result = mcp_client.call_tool("campaign-calendar", payload)
    return str(result)


def available_coupons(user_id: str) -> str:
    """
    查询用户当前可领取的麦麦省优惠券列表。

    参数：
      user_id: 用户 ID

    返回：
      可领取优惠券列表（JSON 字符串）
    """
    payload = {"userId": user_id}
    result = mcp_client.call_tool("available-coupons", payload)
    return str(result)


def auto_bind_coupons(user_id: str) -> str:
    """
    自动领取用户当前可用的所有麦麦省优惠券。

    参数：
      user_id: 用户 ID

    返回：
      领取结果（JSON 字符串）
    """
    payload = {"userId": user_id}
    result = mcp_client.call_tool("auto-bind-coupons", payload)
    return str(result)


def query_my_coupons(user_id: str) -> str:
    """
    查询用户有哪些可用的优惠券。

    参数：
      user_id: 用户 ID

    返回：
      用户优惠券列表（JSON 字符串）
    """
    payload = {"userId": user_id}
    result = mcp_client.call_tool("query-my-coupons", payload)
    return str(result)


def query_my_account(user_id: str) -> str:
    """
    查询用户的积分账户信息。

    参数：
      user_id: 用户 ID

    返回：
      积分账户信息（包括可用积分、累计积分、冻结积分、即将过期积分等）（JSON 字符串）
    """
    payload = {"userId": user_id}
    result = mcp_client.call_tool("query-my-account", payload)
    return str(result)


def mall_points_products(user_id: str = None, limit: int = 50) -> str:
    """
    查询麦麦商城内可以用积分兑换的餐品券列表。

    参数：
      user_id: 用户 ID（可选）
      limit: 返回结果数量限制（默认 50）

    返回：
      积分兑换商品列表（JSON 字符串）
    """
    payload = {"limit": limit}
    if user_id:
        payload["userId"] = user_id
    result = mcp_client.call_tool("mall-points-products", payload)
    return str(result)


def mall_product_detail(product_id: str) -> str:
    """
    查询麦麦商城积分兑换商品的详细信息。

    参数：
      product_id: 商品 ID

    返回：
      商品详情（包括图片、积分、有效期、说明等）（JSON 字符串）
    """
    payload = {"productId": product_id}
    result = mcp_client.call_tool("mall-product-detail", payload)
    return str(result)


def mall_create_order(user_id: str, product_id: str) -> str:
    """
    使用积分在麦麦商城兑换商品。

    参数：
      user_id: 用户 ID
      product_id: 商品 ID

    返回：
      兑换订单号与券码信息（JSON 字符串）
    """
    payload = {
        "userId": user_id,
        "productId": product_id,
    }
    result = mcp_client.call_tool("mall-create-order", payload)
    return str(result)


def now_time_info() -> str:
    """
    获取当前时间信息。

    返回：
      当前的完整时间信息（JSON 字符串）
    """
    payload = {}
    result = mcp_client.call_tool("now-time-info", payload)
    return str(result)


# 全局 MCP 客户端实例（在 main.py 中初始化）
mcp_client: Optional[McpClient] = None


def init_mcp_client(base_url: str, token: str, timeout: int = 10):
    """
    初始化全局 MCP 客户端实例。

    应在应用启动时调用此函数。

    参数：
      base_url: MCP Server 地址
      token: 认证 token
      timeout: 请求超时时间（秒）
    """
    global mcp_client
    mcp_client = McpClient(base_url=base_url, token=token, timeout=timeout)
    logger.info(f"MCP client initialized with base_url: {base_url}")
 
class MCPPClient:
     def __init__(self, base_url, api_key):
         self.base_url = base_url
         self.api_key = api_key
 
     def call_tool(self, tool_name, tool_args):
         url = f"{self.base_url}/tools/{tool_name}"
         headers = {
             "Authorization": f"Bearer {self.api_key}"
         }
         response = requests.post(url, json=tool_args, headers=headers)
         if response.status_code == 200:
             return response.json()
         else:
             raise Exception(f"Error calling MCP tool: {response.status_code} {response.text}")