"""
mcp_client.py - 麦当劳 MCP Server 客户端封装

负责与远程 MCP Server 通信，提供工具调用接口。
支持通用的 MCP 工具调用，以及针对常见业务场景的便利方法。
"""

import os
import logging
import requests
import json
from typing import Dict, Any, Optional

from agentscope.tool import ToolResponse
from agentscope.message import TextBlock

logger = logging.getLogger(__name__)


class McpClient:
    """
    麦当劳 MCP Server 客户端。

    遵循 MCP 标准 JSON-RPC 2.0 握手流程：
      1. initialize - 协商协议版本和能力
      2. initialized - 通知服务器初始化完成
      3. tools/list - 获取可用工具列表（缓存）

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
        self.request_id = 0
        self.tools_cache = None
        self.handshake_success = False
        
        # 执行标准握手流程
        self._perform_handshake()

    def _build_headers(self) -> Dict[str, str]:
        """构建请求 header，包含认证信息。"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
    
    def _get_next_id(self) -> int:
        """获取下一个 RPC 请求 ID。"""
        self.request_id += 1
        return self.request_id
    
    def _send_jsonrpc(
        self, 
        method: str, 
        params: Dict = None, 
        expect_response: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        发送 JSON-RPC 2.0 请求（内部方法）。
        
        参数：
          - method: RPC 方法名
          - params: 方法参数
          - expect_response: 是否期望响应（notifications 不期望响应）
        
        返回：
          响应的 result 字段（如果期望响应）
        """
        url = self.base_url
        headers = self._build_headers()
        
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
        }
        
        if expect_response:
            request_data["id"] = self._get_next_id()
        
        if params:
            request_data["params"] = params
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=request_data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            if not expect_response:
                logger.debug(f"MCP notification '{method}' sent successfully")
                return None
            
            # 解析响应
            result = response.json()
            
            # 检查 RPC 错误响应
            if "error" in result and result["error"] is not None:
                error_info = result["error"]
                error_msg = error_info.get("message", "Unknown error")
                logger.error(f"MCP RPC '{method}' error: {error_msg}")
                return None
            
            logger.debug(f"MCP RPC '{method}' success")
            return result.get("result")
            
        except Exception as e:
            logger.error(f"MCP RPC '{method}' failed: {e}")
            return None
    
    def _perform_handshake(self):
        """
        执行 MCP 标准握手流程。
        
        步骤：
          1. initialize - 建立会话
          2. initialized - 通知服务器
          3. tools/list - 获取工具列表
        """
        logger.info(f"Starting MCP handshake with {self.base_url}")
        
        # 步骤 1: initialize
        logger.debug("[Step 1] Sending initialize request...")
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-agent-client",
                "version": "1.0.0"
            }
        }
        init_result = self._send_jsonrpc("initialize", init_params)
        if init_result is None:
            logger.error("MCP initialize failed, handshake aborted")
            return
        logger.debug(f"Initialize response: {init_result}")
        
        # 步骤 2: initialized
        logger.debug("[Step 2] Sending initialized notification...")
        self._send_jsonrpc("notifications/initialized", expect_response=False)
        
        # 步骤 3: tools/list
        logger.debug("[Step 3] Requesting tools list...")
        tools_result = self._send_jsonrpc("tools/list", {})
        if tools_result is None:
            logger.error("MCP tools/list failed, handshake incomplete")
            return
        
        # 缓存工具列表
        self.tools_cache = tools_result.get("tools", [])
        logger.info(f"MCP handshake success! Cached {len(self.tools_cache)} tools")
        self.handshake_success = True

    def call_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 MCP 工具（使用标准 tools/call 方法）。

        参数：
          - tool_name: MCP 工具名称（如 "query-nearby-stores"）
          - payload: 工具输入参数（字典）

        返回：
          - 工具执行结果（JSON 对象）

        异常：
          - ValueError: 握手失败、网络错误或服务端返回错误
        """
        # 检查握手是否成功
        if not self.handshake_success:
            raise ValueError("MCP handshake failed, tool call not available")
        
        # 使用标准的 tools/call 方法
        tool_params = {
            "name": tool_name,
            "arguments": payload
        }
        
        try:
            result = self._send_jsonrpc("tools/call", tool_params)
            if result is None:
                raise ValueError(f"MCP tool '{tool_name}' call failed")
            
            logger.debug(f"MCP tool '{tool_name}' called successfully")
            return result
        except Exception as e:
            logger.error(f"MCP tool '{tool_name}' call failed: {e}")
            raise ValueError(f"MCP 工具调用失败: {str(e)}")


# ────────────────────────────────────────────────────────────────
# MCP 工具包装函数
# 每个函数对应一个 MCP 工具，AgentScope 可以直接注册这些函数
# ────────────────────────────────────────────────────────────────

def _wrap_tool_result(tool_name: str, result: Any) -> ToolResponse:
    """
    将 MCP 工具结果包装为 AgentScope ToolResponse。
    
    参数：
      tool_name: 工具名称
      result: MCP 工具返回的结果
    
    返回：
      符合 AgentScope 框架要求的 ToolResponse
    """
    try:
        # 转换为 JSON 字符串便于展示
        if isinstance(result, dict):
            content = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            content = str(result)
        
        # 使用 TextBlock 包装内容
        text_block = TextBlock(text=content)
        return ToolResponse(content=[text_block])
    except Exception as e:
        logger.error(f"Failed to wrap tool result for {tool_name}: {e}")
        error_block = TextBlock(text=f"工具调用失败: {str(e)}")
        return ToolResponse(content=[error_block])


def list_nutrition_foods(food_name: str = "") -> ToolResponse:
    """
    列出麦当劳常见餐品的营养信息。

    参数：
      food_name: 餐品名称（可选，用于过滤）

    返回：
      餐品营养信息列表（ToolResponse）
    """
    try:
        payload = {}
        if food_name:
            payload["foodName"] = food_name
        result = mcp_client.call_tool("list-nutrition-foods", payload)
        return _wrap_tool_result("list-nutrition-foods", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def query_nearby_stores(latitude: float, longitude: float) -> ToolResponse:
    """
    查询用户位置附近的麦当劳门店。

    参数：
      latitude: 纬度
      longitude: 经度

    返回：
      附近门店列表（ToolResponse）
    """
    try:
        payload = {
            "latitude": latitude,
            "longitude": longitude,
        }
        result = mcp_client.call_tool("query-nearby-stores", payload)
        return _wrap_tool_result("query-nearby-stores", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def delivery_query_addresses(user_id: str) -> ToolResponse:
    """
    查询用户已保存的配送地址列表。

    参数：
      user_id: 用户 ID

    返回：
      地址列表及对应门店信息（ToolResponse）
    """
    try:
        payload = {"userId": user_id}
        result = mcp_client.call_tool("delivery-query-addresses", payload)
        return _wrap_tool_result("delivery-query-addresses", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def delivery_create_address(
    user_id: str,
    address: str,
    latitude: float = None,
    longitude: float = None,
) -> ToolResponse:
    """
    为用户创建新的配送地址。

    参数：
      user_id: 用户 ID
      address: 地址文本
      latitude: 纬度（可选）
      longitude: 经度（可选）

    返回：
      新创建的地址信息（ToolResponse）
    """
    try:
        payload = {
            "userId": user_id,
            "address": address,
        }
        if latitude is not None:
            payload["latitude"] = latitude
        if longitude is not None:
            payload["longitude"] = longitude
        result = mcp_client.call_tool("delivery-create-address", payload)
        return _wrap_tool_result("delivery-create-address", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def query_store_coupons(store_code: str, user_id: str) -> ToolResponse:
    """
    查询用户在指定门店可使用的优惠券。

    参数：
      store_code: 门店代码
      user_id: 用户 ID

    返回：
      可用优惠券列表（ToolResponse）
    """
    try:
        payload = {
            "storeCode": store_code,
            "userId": user_id,
        }
        result = mcp_client.call_tool("query-store-coupons", payload)
        return _wrap_tool_result("query-store-coupons", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def query_meals(store_code: str) -> ToolResponse:
    """
    查询指定门店当前可售卖的餐品菜单。

    参数：
      store_code: 门店代码

    返回：
      菜单列表（ToolResponse）
    """
    try:
        payload = {"storeCode": store_code}
        result = mcp_client.call_tool("query-meals", payload)
        return _wrap_tool_result("query-meals", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def query_meal_detail(meal_code: str, store_code: str = None) -> ToolResponse:
    """
    查询餐品的详细信息（如套餐组成、默认选择等）。

    参数：
      meal_code: 餐品编码
      store_code: 门店代码（可选）

    返回：
      餐品详情（ToolResponse）
    """
    try:
        payload = {"mealCode": meal_code}
        if store_code:
            payload["storeCode"] = store_code
        result = mcp_client.call_tool("query-meal-detail", payload)
        return _wrap_tool_result("query-meal-detail", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def calculate_price(
    store_code: str,
    items: list,
    coupon_ids: list = None,
) -> ToolResponse:
    """
    计算商品的价格，包括商品金额、配送费、优惠金额等。

    参数：
      store_code: 门店代码
      items: 商品列表，每个商品格式为 {"code": "...", "quantity": ...}
      coupon_ids: 优惠券 ID 列表（可选）

    返回：
      价格计算结果（ToolResponse）
    """
    try:
        payload = {
            "storeCode": store_code,
            "items": items,
        }
        if coupon_ids:
            payload["couponIds"] = coupon_ids
        result = mcp_client.call_tool("calculate-price", payload)
        return _wrap_tool_result("calculate-price", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def create_order(
    store_code: str,
    be_code: str,
    user_id: str,
    items: list,
    dine_in_type: str = "DELIVERY",
    coupon_ids: list = None,
    address_id: str = None,
) -> ToolResponse:
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
      订单详情及支付链接（ToolResponse）
    """
    try:
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
        return _wrap_tool_result("create-order", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def query_order(order_id: str, user_id: str) -> ToolResponse:
    """
    查询订单详情（包括订单状态、内容、配送信息等）。

    参数：
      order_id: 订单 ID
      user_id: 用户 ID

    返回：
      订单信息（ToolResponse）
    """
    try:
        payload = {
            "orderId": order_id,
            "userId": user_id,
        }
        result = mcp_client.call_tool("query-order", payload)
        return _wrap_tool_result("query-order", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def campaign_calendar() -> ToolResponse:
    """
    查询麦当劳中国当月的营销活动日历。

    返回：
      活动日历信息（ToolResponse）
    """
    try:
        payload = {}
        result = mcp_client.call_tool("campaign-calendar", payload)
        return _wrap_tool_result("campaign-calendar", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def available_coupons(user_id: str) -> ToolResponse:
    """
    查询用户当前可领取的麦麦省优惠券列表。

    参数：
      user_id: 用户 ID

    返回：
      可领取优惠券列表（ToolResponse）
    """
    try:
        payload = {"userId": user_id}
        result = mcp_client.call_tool("available-coupons", payload)
        return _wrap_tool_result("available-coupons", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def auto_bind_coupons(user_id: str) -> ToolResponse:
    """
    自动领取用户当前可用的所有麦麦省优惠券。

    参数：
      user_id: 用户 ID

    返回：
      领取结果（ToolResponse）
    """
    try:
        payload = {"userId": user_id}
        result = mcp_client.call_tool("auto-bind-coupons", payload)
        return _wrap_tool_result("auto-bind-coupons", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def query_my_coupons(user_id: str) -> ToolResponse:
    """
    查询用户有哪些可用的优惠券。

    参数：
      user_id: 用户 ID

    返回：
      用户优惠券列表（ToolResponse）
    """
    try:
        payload = {"userId": user_id}
        result = mcp_client.call_tool("query-my-coupons", payload)
        return _wrap_tool_result("query-my-coupons", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def query_my_account(user_id: str) -> ToolResponse:
    """
    查询用户的积分账户信息。

    参数：
      user_id: 用户 ID

    返回：
      积分账户信息（ToolResponse）
    """
    try:
        payload = {"userId": user_id}
        result = mcp_client.call_tool("query-my-account", payload)
        return _wrap_tool_result("query-my-account", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def mall_points_products(user_id: str = None, limit: int = 50) -> ToolResponse:
    """
    查询麦麦商城内可以用积分兑换的餐品券列表。

    参数：
      user_id: 用户 ID（可选）
      limit: 返回结果数量限制（默认 50）

    返回：
      积分兑换商品列表（ToolResponse）
    """
    try:
        payload = {"limit": limit}
        if user_id:
            payload["userId"] = user_id
        result = mcp_client.call_tool("mall-points-products", payload)
        return _wrap_tool_result("mall-points-products", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def mall_product_detail(product_id: str) -> ToolResponse:
    """
    查询麦麦商城积分兑换商品的详细信息。

    参数：
      product_id: 商品 ID

    返回：
      商品详情（ToolResponse）
    """
    try:
        payload = {"productId": product_id}
        result = mcp_client.call_tool("mall-product-detail", payload)
        return _wrap_tool_result("mall-product-detail", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def mall_create_order(user_id: str, product_id: str) -> ToolResponse:
    """
    使用积分在麦麦商城兑换商品。

    参数：
      user_id: 用户 ID
      product_id: 商品 ID

    返回：
      兑换订单号与券码信息（ToolResponse）
    """
    try:
        payload = {
            "userId": user_id,
            "productId": product_id,
        }
        result = mcp_client.call_tool("mall-create-order", payload)
        return _wrap_tool_result("mall-create-order", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


def now_time_info() -> ToolResponse:
    """
    获取当前时间信息。

    返回：
      当前的完整时间信息（ToolResponse）
    """
    try:
        payload = {}
        result = mcp_client.call_tool("now-time-info", payload)
        return _wrap_tool_result("now-time-info", result)
    except Exception as e:
        error_block = TextBlock(text=str(e))
        return ToolResponse(content=[error_block])


# 全局 MCP 客户端实例（在 main.py 中初始化）
mcp_client: Optional[McpClient] = None


def init_mcp_client(base_url: str, token: str, timeout: int = 10) -> bool:
    """
    初始化全局 MCP 客户端实例，并完成标准握手流程。

    应在应用启动时调用此函数。

    参数：
      base_url: MCP Server 地址
      token: 认证 token
      timeout: 请求超时时间（秒）
    
    返回：
      握手是否成功
    """
    global mcp_client
    try:
        mcp_client = McpClient(base_url=base_url, token=token, timeout=timeout)
        
        # 检查握手是否成功
        if mcp_client.handshake_success:
            logger.info(f"✓ MCP client initialized successfully with {base_url}")
            logger.info(f"  Available tools: {len(mcp_client.tools_cache)}")
            return True
        else:
            logger.error(f"✗ MCP client handshake failed with {base_url}")
            return False
    except Exception as e:
        logger.error(f"✗ MCP client initialization failed: {e}")
        return False
