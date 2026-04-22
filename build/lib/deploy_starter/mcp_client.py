"""
mcp_client.py - 双 MCP Server 客户端封装

负责与以下两个 MCP Server 通信：
  - 麦当劳 MCP (mcd_client)：真实麦当劳中国 MCP，提供真实业务数据
  - 星选汉堡 MCP (vstore_client)：本地虚拟商家 MCP，模拟竞品汉堡品牌

设计思路：
  - 两套工具函数，前缀区分：无前缀=麦当劳，vstore_=星选汉堡
  - Agent 同时注册两套工具，遇到对比/选择需求时两家都查
  - 星选汉堡无优惠券体系，麦当劳有完整优惠券体系，形成对比亮点
"""

import os
import logging
import requests
import json
from typing import Dict, Any, Optional, List

from agentscope.tool import ToolResponse
from agentscope.message import TextBlock

logger = logging.getLogger(__name__)


class McpClient:
    """
    MCP Server 客户端（通用）。

    遵循 MCP 标准 JSON-RPC 2.0 握手流程：
      1. initialize - 协商协议版本和能力
      2. initialized - 通知服务器初始化完成
      3. tools/list - 获取可用工具列表（缓存）
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

        self._perform_handshake()

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    def _get_next_id(self) -> int:
        self.request_id += 1
        return self.request_id

    def _send_jsonrpc(
        self,
        method: str,
        params: Dict = None,
        expect_response: bool = True
    ) -> Optional[Dict[str, Any]]:
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
                return None

            result = response.json()
            if "error" in result and result["error"] is not None:
                error_msg = result["error"].get("message", "Unknown error")
                logger.error(f"MCP RPC '{method}' error: {error_msg}")
                return None

            return result.get("result")

        except Exception as e:
            logger.error(f"MCP RPC '{method}' failed: {e}")
            return None

    def _perform_handshake(self):
        logger.info(f"Starting MCP handshake with {self.base_url}")

        init_result = self._send_jsonrpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "mcp-agent-client", "version": "1.0.0"}
        })
        if init_result is None:
            logger.error("MCP initialize failed")
            return

        self._send_jsonrpc("notifications/initialized", expect_response=False)

        tools_result = self._send_jsonrpc("tools/list", {})
        if tools_result is None:
            logger.error("MCP tools/list failed")
            return

        self.tools_cache = tools_result.get("tools", [])
        logger.info(f"MCP handshake success with {self.base_url}! Cached {len(self.tools_cache)} tools")
        self.handshake_success = True

    def call_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.handshake_success:
            raise ValueError("MCP handshake failed, tool call not available")

        result = self._send_jsonrpc("tools/call", {
            "name": tool_name,
            "arguments": payload
        })
        if result is None:
            raise ValueError(f"MCP tool '{tool_name}' call failed")
        return result


# ────────────────────────────────────────────────────────────────
# 工具结果包装
# ────────────────────────────────────────────────────────────────

def _wrap_tool_result(tool_name: str, result: Any) -> ToolResponse:
    """
    将 MCP 工具结果包装为 AgentScope ToolResponse。

    支持三种返回格式：
      1. 真实麦当劳 MCP：{content: [...], isError: bool, structuredContent: [...]}
      2. 星选汉堡/虚拟 MCP 标准格式：{success, code, message, datetime, traceId, data}
      3. 其他格式：直接 JSON dump
    """
    try:
        if isinstance(result, dict):
            # 格式1：真实麦当劳 MCP 返回格式
            if "content" in result or "isError" in result or "structuredContent" in result:
                content_text = ""
                if isinstance(result.get("content"), list) and result["content"]:
                    for item in result["content"]:
                        if isinstance(item, dict) and "text" in item:
                            content_text += item["text"] + "\n"
                if not content_text and result.get("structuredContent"):
                    content_text = json.dumps(result["structuredContent"], ensure_ascii=False, indent=2)
                if not content_text:
                    content_text = json.dumps(result, ensure_ascii=False, indent=2)
                return ToolResponse(content=[TextBlock(text=content_text)])

            # 格式2：虚拟 MCP 标准格式 {success, code, data}
            elif "success" in result and "data" in result:
                if result.get("success"):
                    content = json.dumps(result["data"], ensure_ascii=False, indent=2)
                else:
                    content = f"调用失败: {result.get('message', '未知错误')} (code={result.get('code')})"
                return ToolResponse(content=[TextBlock(text=content)])

            # 格式3：其他字典格式
            else:
                return ToolResponse(content=[TextBlock(
                    text=json.dumps(result, ensure_ascii=False, indent=2)
                )])
        else:
            return ToolResponse(content=[TextBlock(text=str(result))])

    except Exception as e:
        logger.error(f"Failed to wrap tool result for {tool_name}: {e}")
        return ToolResponse(content=[TextBlock(text=f"工具调用失败: {str(e)}")])


# ────────────────────────────────────────────────────────────────
# 麦当劳 MCP 工具包装函数（10个核心工具）
# ────────────────────────────────────────────────────────────────

def query_nearby_stores(searchType: int = 2, beType: int = 1, city: str = None, keyword: str = None) -> ToolResponse:
    """
    【麦当劳】查询用户位置附近的麦当劳门店。

    参数：
      searchType: 1=查询收藏，2=按位置搜索（默认2）
      beType: 默认1（到店）
      city: 城市，searchType=2时必填（如"上海"）
      keyword: 位置关键词，searchType=2时必填（如"南京东路"）

    返回：附近门店列表
    """
    try:
        payload = {"searchType": searchType, "beType": beType}
        if city is not None:
            payload["city"] = city
        if keyword is not None:
            payload["keyword"] = keyword
        
        result = mcd_client.call_tool("query-nearby-stores", payload)
        # 记录工具调用 + 返回结果（供门店名一致性校验使用）
        ToolCallTracker.get_current().record("query_nearby_stores", result)
        
        return _wrap_tool_result("query-nearby-stores", result)
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def query_store_coupons(storeCode: str, beCode: str = None, orderType: int = 1) -> ToolResponse:
    """
    【麦当劳】查询用户在指定麦当劳门店可使用的优惠券。

    参数：
      storeCode: 门店代码（必填）
      beCode: BE编码（可选）
      orderType: 1=到店，2=外送（默认1）

    返回：可用优惠券列表
    """
    try:
        payload = {"storeCode": storeCode, "orderType": orderType}
        if beCode is not None:
            payload["beCode"] = beCode
        return _wrap_tool_result("query-store-coupons", mcd_client.call_tool("query-store-coupons", payload))
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def query_meals(storeCode: str, beCode: str = None, orderType: int = 1) -> ToolResponse:
    """
    【麦当劳】查询指定麦当劳门店当前可售卖的餐品菜单。

    参数：
      storeCode: 门店代码（必填）
      beCode: BE编码（可选）
      orderType: 1=到店，2=外送（默认1）

    返回：菜单列表
    """
    try:
        payload = {"storeCode": storeCode, "orderType": orderType}
        if beCode is not None:
            payload["beCode"] = beCode
        
        result = mcd_client.call_tool("query-meals", payload)
        # 记录工具调用 + 返回结果（供价格校验使用）
        ToolCallTracker.get_current().record("query_meals", result)
        
        return _wrap_tool_result("query-meals", result)
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def query_meal_detail(code: str, storeCode: str = None, beCode: str = None, orderType: int = 1) -> ToolResponse:
    """
    【麦当劳】查询麦当劳餐品的详细信息。

    参数：
      code: 餐品编码（必填）
      storeCode: 门店代码（可选）
      beCode: BE编码（可选）
      orderType: 1=到店，2=外送（默认1）

    返回：餐品详情
    """
    try:
        payload = {"code": code, "orderType": orderType}
        if storeCode is not None:
            payload["storeCode"] = storeCode
        if beCode is not None:
            payload["beCode"] = beCode
        return _wrap_tool_result("query-meal-detail", mcd_client.call_tool("query-meal-detail", payload))
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def calculate_price(storeCode: str, beCode: str = None, orderType: int = 1, items: list = None) -> ToolResponse:
    """
    【麦当劳】计算麦当劳商品价格（含优惠券折扣）。

    参数：
      storeCode: 门店代码（必填）
      beCode: BE编码（可选）
      orderType: 1=到店，2=外送（默认1）
      items: 商品列表，格式：[{"productCode": "...", "quantity": 1, "couponId": "...", "couponCode": "..."}]

    返回：价格计算结果（含原价、折扣、实付价）
    """
    try:
        payload = {"storeCode": storeCode, "orderType": orderType, "items": items or []}
        if beCode is not None:
            payload["beCode"] = beCode
        return _wrap_tool_result("calculate-price", mcd_client.call_tool("calculate-price", payload))
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def create_order(storeCode: str = None, beCode: str = None, addressId: str = None,
                 takeWayCode: str = None, orderType: int = 1,
                 items: List[Dict[str, Any]] = None) -> ToolResponse:
    """
    【麦当劳】创建麦当劳订单。

    参数：
      storeCode: 门店编码（可选）
      beCode: BE编码（可选）
      addressId: 外送场景必填
      takeWayCode: 到店场景必填，从 calculate_price 结果中获取
      orderType: 1=到店，2=外送（默认1）
      items: 商品列表（格式同 calculate_price）

    返回：订单详情及支付链接
    """
    try:
        payload = {"orderType": orderType, "items": items or []}
        if storeCode is not None:
            payload["storeCode"] = storeCode
        if beCode is not None:
            payload["beCode"] = beCode
        if addressId is not None:
            payload["addressId"] = addressId
        if takeWayCode is not None:
            payload["takeWayCode"] = takeWayCode
        return _wrap_tool_result("create-order", mcd_client.call_tool("create-order", payload))
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def query_order(orderId: str) -> ToolResponse:
    """
    【麦当劳】查询麦当劳订单详情。

    参数：
      orderId: 订单号（必填）

    返回：订单信息
    """
    try:
        return _wrap_tool_result("query-order", mcd_client.call_tool("query-order", {"orderId": orderId}))
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def available_coupons() -> ToolResponse:
    """
    【麦当劳】查询用户当前可领取的麦麦省优惠券列表。

    返回：可领取优惠券列表
    """
    try:
        return _wrap_tool_result("available-coupons", mcd_client.call_tool("available-coupons", {}))
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def auto_bind_coupons() -> ToolResponse:
    """
    【麦当劳】自动领取用户当前可用的所有麦麦省优惠券（一键领券）。

    返回：领取结果
    """
    try:
        return _wrap_tool_result("auto-bind-coupons", mcd_client.call_tool("auto-bind-coupons", {}))
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def query_my_coupons() -> ToolResponse:
    """
    【麦当劳】查询用户已有的可用优惠券。

    返回：用户优惠券列表
    """
    try:
        return _wrap_tool_result("query-my-coupons", mcd_client.call_tool("query-my-coupons", {}))
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


# ────────────────────────────────────────────────────────────────
# 星选汉堡 MCP 工具包装函数（6个核心工具，vstore_ 前缀）
# ────────────────────────────────────────────────────────────────

def vstore_query_nearby_stores(searchType: int = 2, beType: int = 1, city: str = None, keyword: str = None) -> ToolResponse:
    """
    【星选汉堡】查询用户位置附近的星选汉堡门店。

    参数：
      searchType: 1=查询收藏，2=按位置搜索（默认2）
      beType: 默认1（到店）
      city: 城市，searchType=2时必填（如"上海"）
      keyword: 位置关键词，searchType=2时必填（如"南京东路"）

    返回：附近星选汉堡门店列表
    """
    try:
        payload = {"searchType": searchType, "beType": beType}
        if city is not None:
            payload["city"] = city
        if keyword is not None:
            payload["keyword"] = keyword
        
        result = vstore_client.call_tool("query-nearby-stores", payload)
        # 记录工具调用 + 返回结果（供门店名一致性校验使用）
        ToolCallTracker.get_current().record("vstore_query_nearby_stores", result)
        
        return _wrap_tool_result("vstore/query-nearby-stores", result)
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def vstore_query_meals(storeCode: str, beCode: str = None, orderType: int = 1) -> ToolResponse:
    """
    【星选汉堡】查询指定星选汉堡门店当前可售卖的餐品菜单。

    参数：
      storeCode: 门店代码（必填，如 SX001）
      beCode: BE编码（可选）
      orderType: 1=到店，2=外送（默认1）

    返回：星选汉堡菜单列表
    """
    try:
        payload = {"storeCode": storeCode, "orderType": orderType}
        if beCode is not None:
            payload["beCode"] = beCode
        
        result = vstore_client.call_tool("query-meals", payload)
        # 记录工具调用 + 返回结果（供价格校验使用）
        ToolCallTracker.get_current().record("vstore_query_meals", result)
        
        return _wrap_tool_result("vstore/query-meals", result)
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def vstore_query_meal_detail(code: str, storeCode: str = None, beCode: str = None, orderType: int = 1) -> ToolResponse:
    """
    【星选汉堡】查询星选汉堡餐品的详细信息。

    参数：
      code: 餐品编码（必填，如 SX_BG001）
      storeCode: 门店代码（可选）
      beCode: BE编码（可选）
      orderType: 1=到店，2=外送（默认1）

    返回：餐品详情
    """
    try:
        payload = {"code": code, "orderType": orderType}
        if storeCode is not None:
            payload["storeCode"] = storeCode
        if beCode is not None:
            payload["beCode"] = beCode
        return _wrap_tool_result("vstore/query-meal-detail", vstore_client.call_tool("query-meal-detail", payload))
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def vstore_calculate_price(storeCode: str, beCode: str = None, orderType: int = 1, items: list = None) -> ToolResponse:
    """
    【星选汉堡】计算星选汉堡商品价格（星选汉堡无优惠券体系，为裸价）。

    参数：
      storeCode: 门店代码（必填）
      beCode: BE编码（可选）
      orderType: 1=到店，2=外送（默认1）
      items: 商品列表，格式：[{"productCode": "...", "quantity": 1}]

    返回：价格计算结果
    """
    try:
        payload = {"storeCode": storeCode, "orderType": orderType, "items": items or []}
        if beCode is not None:
            payload["beCode"] = beCode
        return _wrap_tool_result("vstore/calculate-price", vstore_client.call_tool("calculate-price", payload))
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def vstore_create_order(storeCode: str = None, beCode: str = None, orderType: int = 1,
                        takeWayCode: str = None,
                        items: List[Dict[str, Any]] = None) -> ToolResponse:
    """
    【星选汉堡】创建星选汉堡订单（到店取餐）。

    参数：
      storeCode: 门店编码（可选）
      beCode: BE编码（可选）
      orderType: 1=到店，2=外送（默认1）
      takeWayCode: 取餐方式编码，从 vstore_calculate_price 返回的 takeWayList 中获取（可选，默认 locker-in 自取）
      items: 商品列表，格式：[{"productCode": "...", "quantity": 1}]

    返回：订单详情
    """
    try:
        payload = {"orderType": orderType, "items": items or []}
        if storeCode is not None:
            payload["storeCode"] = storeCode
        if beCode is not None:
            payload["beCode"] = beCode
        if takeWayCode is not None:
            payload["takeWayCode"] = takeWayCode
        return _wrap_tool_result("vstore/create-order", vstore_client.call_tool("create-order", payload))
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


def vstore_query_order(orderId: str) -> ToolResponse:
    """
    【星选汉堡】查询星选汉堡订单详情。

    参数：
      orderId: 订单号（必填）

    返回：订单信息
    """
    try:
        return _wrap_tool_result("vstore/query-order", vstore_client.call_tool("query-order", {"orderId": orderId}))
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])


# ────────────────────────────────────────────────────────────────
# 工具调用链路追踪器
# ────────────────────────────────────────────────────────────────
import threading


class ToolCallTracker:
    """
    线程安全的工具调用记录器（增强版：记录工具返回结果）。

    在每次 Agent 处理一个用户请求时，通过 ToolCallTracker.reset() 创建
    一个新的请求级实例，后续工具函数调用时通过 get_current() 获取并记录。
    校验层通过 was_called() 检查关键工具是否真实执行过，
    通过 get_result() 获取工具返回的原始数据用于一致性校验。
    """
    _local = threading.local()

    @classmethod
    def get_current(cls) -> "ToolCallTracker":
        """获取当前线程的 Tracker 实例（不存在则自动创建）。"""
        if not hasattr(cls._local, "tracker") or cls._local.tracker is None:
            cls._local.tracker = ToolCallTracker()
        return cls._local.tracker

    @classmethod
    def reset(cls):
        """重置当前线程的 Tracker（每次新请求开始前调用）。"""
        cls._local.tracker = ToolCallTracker()

    def __init__(self):
        self._called_tools: set = set()
        self._tool_results: dict = {}  # 新增：记录工具返回结果

    def record(self, tool_name: str, result: Any = None):
        """记录一次工具调用及其返回结果。"""
        self._called_tools.add(tool_name)
        if result is not None:
            self._tool_results[tool_name] = result
        logger.debug(f"[ToolTracker] recorded: {tool_name}")

    def was_called(self, tool_name: str) -> bool:
        """查询指定工具是否在本次请求中被真实调用过。"""
        return tool_name in self._called_tools

    def get_result(self, tool_name: str) -> Any:
        """获取指定工具的返回结果（用于一致性校验）。"""
        return self._tool_results.get(tool_name)

    def all_called(self) -> set:
        """返回本次请求中所有被调用过的工具名集合。"""
        return set(self._called_tools)


# ────────────────────────────────────────────────────────────────
# 全局客户端实例（在 main.py 中初始化）
# ────────────────────────────────────────────────────────────────

mcd_client: Optional[McpClient] = None       # 麦当劳 MCP 客户端
vstore_client: Optional[McpClient] = None    # 星选汉堡 MCP 客户端


def init_mcp_clients(
    mcd_url: str, mcd_token: str, mcd_timeout: int = 10,
    vstore_url: str = None, vstore_token: str = None, vstore_timeout: int = 10,
) -> Dict[str, bool]:
    """
    初始化所有 MCP 客户端实例。

    应在应用启动时调用此函数。

    返回：各客户端握手状态字典，如 {"mcd": True, "vstore": False}
    """
    global mcd_client, vstore_client

    status = {"mcd": False, "vstore": False}

    # 初始化麦当劳客户端
    try:
        mcd_client = McpClient(base_url=mcd_url, token=mcd_token, timeout=mcd_timeout)
        if mcd_client.handshake_success:
            logger.info(f"[MCD] MCP client ready: {mcd_url} ({len(mcd_client.tools_cache)} tools)")
            status["mcd"] = True
        else:
            logger.error(f"[MCD] MCP handshake failed: {mcd_url}")
    except Exception as e:
        logger.error(f"[MCD] MCP client init error: {e}")

    # 初始化星选汉堡客户端
    if vstore_url:
        try:
            vstore_client = McpClient(base_url=vstore_url, token=vstore_token or "", timeout=vstore_timeout)
            if vstore_client.handshake_success:
                logger.info(f"[VSTORE] MCP client ready: {vstore_url} ({len(vstore_client.tools_cache)} tools)")
                status["vstore"] = True
            else:
                logger.error(f"[VSTORE] MCP handshake failed: {vstore_url}")
        except Exception as e:
            logger.error(f"[VSTORE] MCP client init error: {e}")
    else:
        logger.warning("[VSTORE] VSTORE_SERVER_URL not configured, star-select burger tools unavailable")

    return status
