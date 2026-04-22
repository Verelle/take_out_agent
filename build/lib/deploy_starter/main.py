"""
deploy_starter/main.py
======================
BridgeX 项目 · AI 智能体服务入口

本文件基于 阿里云百炼 AgentScope Runtime 框架，构建并启动一个
具有 ReAct 推理能力的对话 Agent（名为 Friday），支持：
  - 多轮对话（依赖 session 记忆）
  - 双 MCP 工具调用（麦当劳 + 星选汉堡虚拟商家）
  - 跨商家价格对比与优惠券优化
  - 流式输出
  - 可观测性追踪（Trace）
"""
import asyncio
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

# ── MCP 客户端导入 ───────────────────────────────────────────────────────────
try:
    from mcp_client import (
        init_mcp_clients,
        ToolCallTracker,
        # 麦当劳工具（10个）
        query_nearby_stores,
        query_store_coupons,
        query_meals,
        query_meal_detail,
        calculate_price,
        create_order,
        query_order,
        available_coupons,
        auto_bind_coupons,
        query_my_coupons,
        # 星选汉堡工具（6个）
        vstore_query_nearby_stores,
        vstore_query_meals,
        vstore_query_meal_detail,
        vstore_calculate_price,
        vstore_create_order,
        vstore_query_order,
    )
except ModuleNotFoundError:
    from deploy_starter.mcp_client import (
        init_mcp_clients,
        ToolCallTracker,
        query_nearby_stores,
        query_store_coupons,
        query_meals,
        query_meal_detail,
        calculate_price,
        create_order,
        query_order,
        available_coupons,
        auto_bind_coupons,
        query_my_coupons,
        vstore_query_nearby_stores,
        vstore_query_meals,
        vstore_query_meal_detail,
        vstore_calculate_price,
        vstore_create_order,
        vstore_query_order,
    )

# ── AgentScope 核心组件 ──────────────────────────────────────────────────────
from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.pipeline import stream_printing_messages
from agentscope.tool import Toolkit, execute_python_code

# ── AgentScope Runtime 适配层 ────────────────────────────────────────────────
from agentscope_runtime.adapters.agentscope.memory import AgentScopeSessionHistoryMemory
from agentscope_runtime.engine import AgentApp, LocalDeployManager
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from agentscope_runtime.engine.services.agent_state import InMemoryStateService
from agentscope_runtime.engine.services.session_history import (
    InMemorySessionHistoryService,
)
from agentscope_runtime.engine.tracing import TraceType, trace


# ── 配置读取 ─────────────────────────────────────────────────────────────────

def read_config():
    """读同目录下的 config.yml 文件，解析为 Python 字典。"""
    config_path = os.path.join(os.path.dirname(__file__), "config.yml")
    config = {}
    with open(config_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    config[key] = value
    return config


config = read_config()


# ── 应用容器初始化 ────────────────────────────────────────────────────────────

agent_app = AgentApp(
    app_name=config.get("APP_NAME"),
    app_description="BridgeX 生活顾问 - 跨商家智能点餐助手",
)


# ── 生命周期管理 ──────────────────────────────────────────────────────────────

@agent_app.init
async def init_func(self):
    """服务启动时的初始化钩子：启动内存服务，初始化双 MCP 客户端。"""
    self.state_service = InMemoryStateService()
    self.session_service = InMemorySessionHistoryService()
    await self.state_service.start()
    await self.session_service.start()

    # 读取 MCP 配置（环境变量优先，回退到 config.yml）
    mcd_url = os.getenv("MCP_SERVER_URL") or config.get("MCP_SERVER_URL")
    mcd_token = os.getenv("MCP_TOKEN") or config.get("MCP_TOKEN")
    mcd_timeout = int(os.getenv("MCP_TIMEOUT", config.get("MCP_TIMEOUT", 10)))

    vstore_url = os.getenv("VSTORE_SERVER_URL") or config.get("VSTORE_SERVER_URL")
    vstore_token = os.getenv("VSTORE_TOKEN") or config.get("VSTORE_TOKEN")
    vstore_timeout = int(os.getenv("VSTORE_TIMEOUT", config.get("VSTORE_TIMEOUT", 10)))

    # 初始化双 MCP 客户端
    status = init_mcp_clients(
        mcd_url=mcd_url, mcd_token=mcd_token, mcd_timeout=mcd_timeout,
        vstore_url=vstore_url, vstore_token=vstore_token, vstore_timeout=vstore_timeout,
    )

    print(f"{'✓' if status['mcd'] else '✗'} 麦当劳 MCP: {mcd_url}")
    print(f"{'✓' if status['vstore'] else '✗'} 星选汉堡 MCP: {vstore_url}")
    if not status["mcd"] and not status["vstore"]:
        print("  ⚠ 所有 MCP 客户端初始化失败，工具将不可用")


@agent_app.shutdown
async def shutdown_func(self):
    """服务关闭时的清理钩子。"""
    for svc in [getattr(self, "state_service", None), getattr(self, "session_service", None)]:
        if svc is not None:
            await svc.stop()


# ── HTTP 路由端点 ─────────────────────────────────────────────────────────────

@agent_app.endpoint("/")
@trace(trace_type=TraceType.LLM, trace_name="llm_func", is_root_span=True)
def read_root():
    return {"hi, i'm running"}


@agent_app.endpoint("/health")
@trace(trace_type=TraceType.LLM, trace_name="llm_func", is_root_span=True)
def health_check():
    return "OK"


# ── 工具链路校验 ──────────────────────────────────────────────────────────────

def _contains_price_info(text: str) -> bool:
    """检测回复是否包含价格数字（¥28、28元、售价、裸价等）。"""
    return bool(re.search(
        r'[¥￥]\s*\d+|\d+\s*元|售价|裸价|到手价|优惠后|实付',
        text
    ))


def _extract_store_names(result: any) -> list:
    """
    从 query_nearby_stores / vstore_query_nearby_stores 的原始返回结果中
    提取所有门店名称，封装两种 MCP 返回格式的差异。

    麦当劳 MCP 格式: {content: [{text: "...JSON..."}]}
    星选汉堡 MCP 格式: {success: True, data: [{storeName: ...}]}
    """
    names = []
    if not isinstance(result, dict):
        return names
    try:
        # 格式1：麦当劳 MCP（content[].text 内嵌 JSON）
        if "content" in result:
            for item in result.get("content", []):
                text = item.get("text", "") if isinstance(item, dict) else ""
                # 尝试转义内嵌的 JSON
                try:
                    inner = json.loads(text)
                    data = inner.get("data", [])
                    if isinstance(data, list):
                        for store in data:
                            if isinstance(store, dict) and "storeName" in store:
                                names.append(store["storeName"])
                except (json.JSONDecodeError, AttributeError):
                    # text 不是纯 JSON，用正则挙出 storeName 字段
                    matches = re.findall(r'"storeName"\s*:\s*"([^"]+)"', text)
                    names.extend(matches)

        # 格式2：星选汉堡 MCP（标准 {success, data} 格式）
        elif "success" in result and isinstance(result.get("data"), list):
            for store in result["data"]:
                if isinstance(store, dict) and "storeName" in store:
                    names.append(store["storeName"])
    except Exception as e:
        logger.warning(f"[StoreNameExtract] 提取门店名失败: {e}")
    return names


def _validate_tool_chain_for_price(reply_text: str) -> tuple:
    """
    校验：
    1. 如果回复包含价格，必须调用过对应商家的菜单查询工具
    2. 如果回复包含门店名称，必须与工具返回的门店名完全一致

    返回：(是否通过, 失败原因)
    """
    if not _contains_price_info(reply_text):
        # 回复里没价格，但仍需校验门店名
        pass

    tracker = ToolCallTracker.get_current()

    # ―― 价格工具链路校验 ――
    if _contains_price_info(reply_text):
        if "星选" in reply_text and not tracker.was_called("vstore_query_meals"):
            return False, "回复包含星选汉堡价格，但未调用 vstore_query_meals 工具获取真实菜单数据"

        if ("麦当劳" in reply_text or "麦辣" in reply_text or "巨无霸" in reply_text) \
                and not tracker.was_called("query_meals"):
            return False, "回复包含麦当劳价格，但未调用 query_meals 工具获取真实菜单数据"

    # ―― 门店名一致性校验 ――
    # 麦当劳：从回复中提取所有提到的麦当劳门店名
    mcd_result = tracker.get_result("query_nearby_stores")
    if mcd_result:
        valid_mcd_stores = _extract_store_names(mcd_result)
        if valid_mcd_stores:
            # 正则：报麦当劳店名（麦当劳 + 任意文字 + 餐厅/店结尾）
            mentioned = re.findall(r'麦当劳[一-龥(-)（）A-Za-z0-9·・—\-　\s]+?(?:餐厅|店)', reply_text)
            for name in mentioned:
                name = name.strip()
                if name and name not in valid_mcd_stores:
                    return False, (
                        f"回复中的麦当劳门店名「{name}」与工具返回不一致。"
                        f"真实门店名应为：{', '.join(valid_mcd_stores)}"
                    )

    # 星选汉堡：从回复中提取所有提到的星选汉堡门店名
    vstore_result = tracker.get_result("vstore_query_nearby_stores")
    if vstore_result:
        valid_vstore_stores = _extract_store_names(vstore_result)
        if valid_vstore_stores:
            mentioned = re.findall(r'星选汉堡[一-龥(-)（）A-Za-z0-9·・—\-　\s]+?(?:餐厅|店)', reply_text)
            for name in mentioned:
                name = name.strip()
                if name and name not in valid_vstore_stores:
                    return False, (
                        f"回复中的星选汉堡门店名「{name}」与工具返回不一致。"
                        f"真实门店名应为：{', '.join(valid_vstore_stores)}"
                    )

    return True, ""


def _build_toolkit() -> Toolkit:
    """构建并返回注册了全部工具的 Toolkit 实例。"""
    toolkit = Toolkit()
    toolkit.register_tool_function(execute_python_code)
    # 麦当劳工具（10个）
    toolkit.register_tool_function(query_nearby_stores)
    toolkit.register_tool_function(query_store_coupons)
    toolkit.register_tool_function(query_meals)
    toolkit.register_tool_function(query_meal_detail)
    toolkit.register_tool_function(calculate_price)
    toolkit.register_tool_function(create_order)
    toolkit.register_tool_function(query_order)
    toolkit.register_tool_function(available_coupons)
    toolkit.register_tool_function(auto_bind_coupons)
    toolkit.register_tool_function(query_my_coupons)
    # 星选汉堡工具（6个）
    toolkit.register_tool_function(vstore_query_nearby_stores)
    toolkit.register_tool_function(vstore_query_meals)
    toolkit.register_tool_function(vstore_query_meal_detail)
    toolkit.register_tool_function(vstore_calculate_price)
    toolkit.register_tool_function(vstore_create_order)
    toolkit.register_tool_function(vstore_query_order)
    return toolkit


_SYS_PROMPT = """你是 Friday，一位专业的生活顾问，专注于帮助用户以最优惠的价格完成餐饮点单。

【你能接入的商家】
你目前同时接入了两家汉堡品牌的 MCP 服务：
1. 🍔 麦当劳（McDonald's）— 真实门店数据，有完整的优惠券体系（麦麦省）
2. ⭐ 星选汉堡（Star Select Burger）— 连锁汉堡品牌，价格较麦当劳低5-15%，暂无优惠券活动

【核心工作理念：帮用户省钱】
每当用户提出点餐需求，你的目标不只是"帮他下单"，而是"帮他用最低的价格点到想要的东西"。
具体做法：
  1. 两家门店都查一遍（query_nearby_stores + vstore_query_nearby_stores）
  2. 两家菜单都看一眼，找到对应品类（query_meals + vstore_query_meals）
  3. 麦当劳先查优惠券（available_coupons / query_my_coupons）
  4. 两家分别算价格（calculate_price + vstore_calculate_price）
  5. 对比结果，给出清晰推荐：星选汉堡裸价 vs 麦当劳用券后价格，哪个合适推哪个
  6. 用户确认后再下单

【信息收集规则】
❌ 禁止假设用户的位置
✅ 查门店前，先从对话中提取位置信息（城市 + 位置关键词）
  - 如果用户已说"我在上海南京东路"→ 直接用
  - 如果用户没提位置 → 礼貌询问："请问您现在在哪个城市/位置？"

❌ 禁止凭空生成任何价格、菜单、门店数据
✅ 所有业务数据必须通过工具获取：
  • 麦当劳附近门店 → query_nearby_stores
  • 麦当劳菜单 → query_meals
  • 麦当劳餐品详情 → query_meal_detail
  • 麦当劳优惠券（可领取） → available_coupons
  • 麦当劳优惠券（已有） → query_my_coupons
  • 麦当劳一键领券 → auto_bind_coupons
  • 麦当劳门店优惠券 → query_store_coupons
  • 麦当劳价格计算 → calculate_price
  • 麦当劳下单 → create_order
  • 麦当劳查订单 → query_order
  • 星选汉堡附近门店 → vstore_query_nearby_stores
  • 星选汉堡菜单 → vstore_query_meals
  • 星选汉堡餐品详情 → vstore_query_meal_detail
  • 星选汉堡价格计算 → vstore_calculate_price
  • 星选汉堡下单 → vstore_create_order
  • 星选汉堡查订单 → vstore_query_order

【当前支持场景】
- 到店取餐（orderType=1）为主，流程最完整
- 外送（orderType=2）暂不推荐，因需要地址管理系统支持

【用户信息处理】
- 当前无用户账号系统，用户通过自然语言提供信息即可
- 需要知道用户位置时主动询问
- 下单所需的取餐方式（takeWayCode）从 calculate_price 结果中获取

【回复风格】
- 中文回复，语气亲切自然
- 对比结果要清晰直观（推荐用表格或分点展示）
- 工具返回数据要整理后呈现，不要直接粘贴原始 JSON
- 如果工具返回失败，如实告知用户，不编造数据

【关键字段输出规则——严格执行】
❌ 严禁对工具返回的门店名称、地址做任何形式的改写、简化、美化或"纠正"
✅ 门店名称必须与工具返回完全一致，一字不差
   示例：工具返回「麦当劳上海黄浦华旭国际大厦餐厅」→ 输出必须是「麦当劳上海黄浦华旭国际大厦餐厅」
   示例：工具返回「麦当劳上海福州路餐厅」→ 输出必须是「麦当劳上海福州路餐厅」
✅ 地址信息必须与工具返回完全一致，不得修改任何字符（包括路名、数字、标点）
   示例：工具返回「西藏中路336号」→ 输出必须是「西藏中路336号」，不得改为其他任何写法
✅ 价格数字必须来自工具返回结果，不得估算、四舍五入或凭空填写"""


# ── 核心对话处理逻辑 ──────────────────────────────────────────────────────────

@agent_app.query(framework="agentscope")
@trace(trace_type=TraceType.LLM, trace_name="llm_func", is_root_span=True)
async def query_func(
    self,
    msgs,
    request: AgentRequest = None,
    **kwargs,
):
    """主对话处理函数，每次用户发消息时调用。"""
    assert kwargs is not None, "kwargs is Required for query_func"

    session_id = request.session_id
    user_id = request.user_id

    state = await self.state_service.export_state(
        session_id=session_id,
        user_id=user_id,
    )

    # ── 工具链路校验 + 重试循环 ───────────────────────────────────────────────
    MAX_RETRY = 3
    current_msgs = msgs
    final_msg = None
    last_flag = None
    agent = None

    for attempt in range(MAX_RETRY):
        # 每次循环开始前重置工具调用记录器
        ToolCallTracker.reset()

        agent = ReActAgent(
            name="Friday",
            model=DashScopeChatModel(
                config.get("DASHSCOPE_MODEL_NAME"),
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                enable_thinking=True,
                stream=True,
                generate_args={"temperature": config.get("LLM_TEMPERATURE", 0.1)},
            ),
            sys_prompt=_SYS_PROMPT,
            toolkit=_build_toolkit(),
            memory=AgentScopeSessionHistoryMemory(
                service=self.session_service,
                session_id=session_id,
                user_id=user_id,
            ),
            formatter=DashScopeChatFormatter(),
        )

        if state:
            agent.load_state_dict(state)

        async for msg, is_last in stream_printing_messages(
            agents=[agent],
            coroutine_task=agent(current_msgs),
        ):
            final_msg = msg
            last_flag = is_last

        # ── 提取回复文本，执行工具链路校验 ──────────────────────────────────
        reply_text = ""
        if final_msg is not None:
            blocks = getattr(final_msg, "content", [])
            if isinstance(blocks, list):
                reply_text = " ".join(
                    b.text for b in blocks if hasattr(b, "text")
                )
            elif isinstance(blocks, str):
                reply_text = blocks

        ok, reason = _validate_tool_chain_for_price(reply_text)

        if ok:
            break  # ✅ 校验通过，退出重试循环
        else:
            print(f"[工具链路校验失败] {reason}，第 {attempt + 1} 次重试")
            # 注入纠错指令，强制模型重新走工具链路
            current_msgs = Msg(
                name="user",
                content=(
                    f"你刚才的回复存在问题：{reason}。"
                    "请严格按照工具返回的原始数据重新回复："
                    "① 禁止假设、估算或改写任何价格、门店名、地址；"
                    "② 如需查询价格，必须重新调用 vstore_query_meals 或 query_meals 工具；"
                    "③ 门店名称和地址必须与工具返回结果完全一致，一字不差。"
                ),
                role="user",
            )

    # ── 输出最终消息给用户 ───────────────────────────────────────────────────
    if final_msg is not None:
        yield final_msg, last_flag

    # ── 保存 Agent 状态 ──────────────────────────────────────────────────────
    if agent is not None:
        state = agent.state_dict()
        await self.state_service.save_state(
            user_id=user_id,
            session_id=session_id,
            state=state,
        )


# ── 可观测性测试函数 ──────────────────────────────────────────────────────────

@trace(trace_type=TraceType.OTHER, trace_name="testObservability", is_root_span=True)
def testObservability():
    print("testObservability")


# ── 服务启动入口 ──────────────────────────────────────────────────────────────

async def main():
    deployer = LocalDeployManager(
        host=config.get("FC_START_HOST", "127.0.0.1"),
        port=config.get("PORT", 8080),
    )
    testObservability()
    await agent_app.deploy(deployer)
    print("Service started, press Ctrl+C to stop...")
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nStopping service...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nService stopped")
