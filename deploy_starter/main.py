"""
deploy_starter/main.py
======================
BridgeX 项目 · AI 智能体服务入口

本文件基于 阿里云百炼 AgentScope Runtime 框架，构建并启动一个
具有 ReAct 推理能力的对话 Agent（名为 Friday），支持：
  - 多轮对话（依赖 session 记忆）
  - 工具调用（默认注册了 execute_python_code）
  - 流式输出
  - 可观测性追踪（Trace）
"""
import asyncio  # 异步事件循环
import json      # JSON 处理（此处备用，框架内部会用到）
import os        # 读取环境变量（如 DASHSCOPE_API_KEY）

# ── MCP 客户端导入 ───────────────────────────────────────────────────────────
try:
    from mcp_client import (
        init_mcp_client,
        list_nutrition_foods,
        query_nearby_stores,
        delivery_query_addresses,
        delivery_create_address,
        query_store_coupons,
        query_meals,
        query_meal_detail,
        calculate_price,
        create_order,
        query_order,
        campaign_calendar,
        available_coupons,
        auto_bind_coupons,
        query_my_coupons,
        query_my_account,
        mall_points_products,
        mall_product_detail,
        mall_create_order,
        now_time_info,
    )
except ModuleNotFoundError:
    from deploy_starter.mcp_client import (
        init_mcp_client,
        list_nutrition_foods,
        query_nearby_stores,
        delivery_query_addresses,
        delivery_create_address,
        query_store_coupons,
        query_meals,
        query_meal_detail,
        calculate_price,
        create_order,
        query_order,
        campaign_calendar,
        available_coupons,
        auto_bind_coupons,
        query_my_coupons,
        query_my_account,
        mall_points_products,
        mall_product_detail,
        mall_create_order,
        now_time_info,
    )

# ── AgentScope 核心组件 ──────────────────────────────────────────────────────
from agentscope.agent import ReActAgent          # ReAct 推理 Agent（思考→工具→回答循环）
from agentscope.formatter import DashScopeChatFormatter  # 消息格式适配 DashScope 接口
from agentscope.model import DashScopeChatModel  # 阿里云百炼大模型接口
from agentscope.pipeline import stream_printing_messages  # 流式输出辅助函数
from agentscope.tool import Toolkit, execute_python_code  # 工具集 + Python 代码执行工具

# ── AgentScope Runtime 适配层 ────────────────────────────────────────────────
from agentscope_runtime.adapters.agentscope.memory import AgentScopeSessionHistoryMemory
# ↑ 将会话历史记忆与 AgentScope Agent 对接，实现多轮对话

from agentscope_runtime.engine import AgentApp, LocalDeployManager
# ↑ AgentApp：应用容器（装载路由、生命周期）
# ↑ LocalDeployManager：本地部署管理器（监听 host:port）

from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
# ↑ 请求体 Schema，包含 session_id、user_id 等

from agentscope_runtime.engine.services.agent_state import InMemoryStateService
# ↑ 内存级 Agent 状态服务（保存 agent 的内部状态，如工具调用历史）

from agentscope_runtime.engine.services.session_history import (
    InMemorySessionHistoryService,
)
# ↑ 内存级会话历史服务（保存对话消息记录，实现多轮上下文）

from agentscope_runtime.engine.tracing import TraceType, trace
# ↑ 可观测性追踪装饰器，用于记录 LLM 调用链路


# ── 配置读取 ─────────────────────────────────────────────────────────────────

def read_config():
    """
    读同目录下的 config.yml 文件，解析为 Python 字典。

    支持的值类型：
      - 字符串（去掉引号）
      - 布尔值（true/false → True/False）
      - 整数（纯数字字符串 → int）

    注意：这是一个极简解析器，不支持嵌套结构，仅适用于 key: value 格式。
    """
    config_path = os.path.join(os.path.dirname(__file__), "config.yml")
    config = {}
    with open(config_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释行
            if line and not line.startswith("#"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    # 类型转换
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    config[key] = value
    return config


# 读取配置（在模块级别执行，程序启动时加载一次）
config = read_config()


# ── 应用容器初始化 ────────────────────────────────────────────────────────────

# 创建 AgentApp 实例，app_name 从配置文件读取
agent_app = AgentApp(
    app_name=config.get("APP_NAME"),
    app_description="A helpful assistant",
)


# ── 生命周期管理 ──────────────────────────────────────────────────────────────

@agent_app.init
async def init_func(self):
    """
    服务启动时的初始化钩子。

    负责创建并启动两个核心服务，以及初始化 MCP 客户端：
      1. InMemoryStateService   —— 存储 Agent 内部状态（如工具调用上下文）
      2. InMemorySessionHistoryService —— 存储对话历史（多轮上下文记忆）
      3. McpClient —— 麦当劳 MCP Server 客户端

    注意：这两个服务都是纯内存存储，重启后数据会丢失。
    生产环境可替换为持久化实现（如 Redis、数据库）。
    """
    self.state_service = InMemoryStateService()
    self.session_service = InMemorySessionHistoryService()
    await self.state_service.start()
    await self.session_service.start()
    
    # 初始化 MCP 客户端
    mcp_url = os.getenv("MCP_SERVER_URL") or config.get("MCP_SERVER_URL")
    mcp_token = os.getenv("MCP_TOKEN") or config.get("MCP_TOKEN")
    mcp_timeout = int(os.getenv("MCP_TIMEOUT", config.get("MCP_TIMEOUT", 10)))
    
    if mcp_url and mcp_token:
        init_mcp_client(base_url=mcp_url, token=mcp_token, timeout=mcp_timeout)
    else:
        print("警告：未配置 MCP_SERVER_URL 和 MCP_TOKEN，MCP 工具将不可用")


@agent_app.shutdown
async def shutdown_func(self):
    """
    服务关闭时的清理钩子。

    优雅地停止两个内存服务，释放资源。
    """
    state_service = getattr(self, "state_service", None)
    session_service = getattr(self, "session_service", None)
    if state_service is not None:
        await state_service.stop()
    if session_service is not None:
        await session_service.stop()


# ── HTTP 路由端点 ─────────────────────────────────────────────────────────────

@agent_app.endpoint("/")
@trace(trace_type=TraceType.LLM, trace_name="llm_func", is_root_span=True)
def read_root():
    """
    根路径端点，用于验证服务是否在线。
    访问 http://host:port/ 会返回一个确认消息。
    """
    return {"hi, i'm running"}


@agent_app.endpoint("/health")
@trace(trace_type=TraceType.LLM, trace_name="llm_func", is_root_span=True)
def health_check():
    """
    健康检查端点，供负载均衡器或监控系统调用。
    返回 "OK" 表示服务正常。
    """
    return "OK"


# ── 核心对话处理逻辑 ──────────────────────────────────────────────────────────

@agent_app.query(framework="agentscope")
@trace(trace_type=TraceType.LLM, trace_name="llm_func", is_root_span=True)
async def query_func(
    self,
    msgs,
    request: AgentRequest = None,
    **kwargs,
):
    """
    主对话处理函数，每次用户发消息时都会调用。

    处理流程：
      1. 从请求中提取 session_id 和 user_id（用于隔离不同用户的对话）
      2. 尝试恢复上次保存的 Agent 状态（实现跨请求的上下文连续性）
      3. 构建工具集（当前注册了 execute_python_code，支持 Agent 执行 Python 代码）
      4. 初始化 ReActAgent（Friday），绑定大模型、工具、记忆
      5. 流式执行 Agent，逐步 yield 消息给调用方
      6. 对话结束后保存最新的 Agent 状态

    参数说明：
      - self    : AgentApp 实例（提供 state_service 和 session_service）
      - msgs    : 本次输入的消息列表
      - request : 包含 session_id、user_id 等元数据
      - kwargs  : 其他扩展参数（框架要求必须存在）
    """
    assert kwargs is not None, "kwargs is Required for query_func"

    # 从请求中提取会话标识
    session_id = request.session_id
    user_id = request.user_id

    # 尝试从状态服务中恢复 Agent 的上一次状态
    # （如果是新会话，state 为空，Agent 从零开始）
    state = await self.state_service.export_state(
        session_id=session_id,
        user_id=user_id,
    )

    # 初始化工具集，并注册工具函数
    # Agent 可以通过工具调用来执行代码、访问麦当劳 MCP 等
    toolkit = Toolkit()
    toolkit.register_tool_function(execute_python_code)
    
    # 注册麦当劳 MCP 工具
    # 查询类工具
    toolkit.register_tool_function(list_nutrition_foods)
    toolkit.register_tool_function(query_meals)
    toolkit.register_tool_function(query_meal_detail)
    toolkit.register_tool_function(query_nearby_stores)
    toolkit.register_tool_function(query_order)
    toolkit.register_tool_function(now_time_info)
    
    # 地址与门店工具
    toolkit.register_tool_function(delivery_query_addresses)
    toolkit.register_tool_function(delivery_create_address)
    toolkit.register_tool_function(query_store_coupons)
    
    # 价格与下单工具
    toolkit.register_tool_function(calculate_price)
    toolkit.register_tool_function(create_order)
    
    # 优惠券工具
    toolkit.register_tool_function(available_coupons)
    toolkit.register_tool_function(auto_bind_coupons)
    toolkit.register_tool_function(query_my_coupons)
    
    # 积分商城工具
    toolkit.register_tool_function(query_my_account)
    toolkit.register_tool_function(mall_points_products)
    toolkit.register_tool_function(mall_product_detail)
    toolkit.register_tool_function(mall_create_order)
    
    # 营销工具
    toolkit.register_tool_function(campaign_calendar)

    # 构建 ReActAgent（Friday）
    # ReAct = Reasoning + Acting，Agent 会先思考再决定是否调用工具
    agent = ReActAgent(
        name="Friday",
        model=DashScopeChatModel(
            config.get("DASHSCOPE_MODEL_NAME"),   # 模型名称，如 qwen-max
            api_key=os.getenv("DASHSCOPE_API_KEY"),  # API Key 从环境变量读取（安全！不写死在代码里）
            enable_thinking=True,   # 启用模型内部思考链（提升推理质量）
            stream=True,            # 启用流式输出（边生成边返回）
        ),
        sys_prompt="""你是麦当劳中国智能点餐助手，名字是 Friday。

你的核心职责是：
1. 帮助用户查询麦当劳菜单、餐品营养信息
2. 为用户推荐菜品搭配（基于品味、营养、价格等）
3. 帮助用户在线点餐、支付订单
4. 告知用户订单状态、配送信息
5. 分享优惠券、积分兑换等会员权益

重要声明：
- 所有关于菜单、价格、订单、门店信息等必须通过麦当劳 MCP 工具查询，不允许凭空编造
- 用户的送餐地址、订单历史、优惠券等个人信息需调用相应工具获取
- 如果用户需求不清晰，请礼貌地追问以获得更多信息
- 始终用中文回复，语气亲切自然，体现麦当劳品牌的友好风格

请记住：真实数据优先于文本生成。""",  # 系统提示词，定义 Agent 人格
        toolkit=toolkit,            # 绑定工具集
        memory=AgentScopeSessionHistoryMemory(
            service=self.session_service,  # 使用内存会话历史服务
            session_id=session_id,         # 按 session 隔离对话历史
            user_id=user_id,               # 按 user 隔离用户数据
        ),
        formatter=DashScopeChatFormatter(),  # 消息格式适配器
    )

    # 如果有历史状态，加载进 Agent（恢复上下文）
    if state:
        agent.load_state_dict(state)

    # 流式执行 Agent，每产出一条消息就 yield 给调用方
    # last 标志表示这是否是最后一条消息
    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last

    # 对话完成后，保存 Agent 当前状态，供下次请求恢复使用
    state = agent.state_dict()
    await self.state_service.save_state(
        user_id=user_id,
        session_id=session_id,
        state=state,
    )


# ── 可观测性测试函数 ──────────────────────────────────────────────────────────

@trace(trace_type=TraceType.OTHER, trace_name="testObservability", is_root_span=True)
def testObservability():
    """
    可观测性功能测试函数。
    服务启动时调用一次，用于验证追踪系统是否正常工作。
    在生产环境中可以删除或替换为真实的启动检查逻辑。
    """
    print("testObservability")


# ── 服务启动入口 ──────────────────────────────────────────────────────────────

async def main():
    """
    异步主函数，负责启动 Agent 服务。

    步骤：
      1. 创建 LocalDeployManager，绑定监听地址和端口
         - host 默认读取环境变量 FC_START_HOST，若未设置则用 127.0.0.1
         - port 默认读取配置文件 PORT，若未设置则用 8080
      2. 调用可观测性测试函数（验证追踪系统）
      3. 部署 agent_app（注册路由、启动服务器）
      4. 等待用户按 Ctrl+C 中断，保持服务常驻
    """
    deployer = LocalDeployManager(
        host=config.get("FC_START_HOST", "127.0.0.1"),
        port=config.get("PORT", 8080),
    )
    testObservability()

    # 部署应用
    await agent_app.deploy(deployer)

    # 保持服务运行，直到用户手动中断
    print("Service started, press Ctrl+C to stop...")
    try:
        await asyncio.Event().wait()  # 永久等待（不会超时），相当于 while True
    except KeyboardInterrupt:
        print("\nStopping service...")


# ── 程序入口 ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        asyncio.run(main())  # 启动异步事件循环，运行 main()
    except KeyboardInterrupt:
        print("\nService stopped")
