# 项目摘要 (PROJECT.md)

快速了解项目全貌，无需深入代码即可获得项目概况和技术方案。

---

## 1. 项目概述

**项目名称**：ModelStudio Agent Starter（麦当劳中国智能点餐助手）

**项目目标**：构建一个基于 AgentScope + 麦当劳 MCP Server 的 AI 智能体，能够帮助用户查询菜单、推荐餐品、下单、查询优惠券等。

**核心特性**：
- ✅ 多轮对话（基于 Session 记忆）
- ✅ 工具调用（Agent 自动调用 MCP 工具获取真实数据）
- ✅ 流式输出（支持边生成边输出）
- ✅ 会话隔离（用户和会话独立管理）
- ✅ 可观测性（内置链路追踪）

---

## 2. 快速启动

### 前置条件
- Python 3.10+
- 已安装依赖：`pip install -r requirements.txt`
- 麦当劳 MCP Server 地址和 Token（可选，但建议配置）

### 启动命令
```bash
cd deploy_starter
python main.py
```

### 验证服务
```bash
curl http://127.0.0.1:8080/health  # 期望返回 "OK"
```

### 配置 MCP
```powershell
$env:MCP_SERVER_URL = "https://your-mcp-server"
$env:MCP_TOKEN = "your-token"
```

---

## 3. 核心架构

### 3.1 整体流程

```
┌──────────────────────────────────────────────────────────────────┐
│  客户端请求                                                       │
│  (HTTP POST /process)                                           │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  main.py - query_func()                                         │
│  - 接收用户消息                                                   │
│  - 初始化 Toolkit 工具集 (20 个 MCP 工具)                         │
│  - 构建 ReActAgent (Friday)                                     │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  ReActAgent 推理循环                                             │
│  - 读取 sys_prompt（强制使用工具）                               │
│  - 思考 (Thinking)→ 决策→ 执行 (Acting)                          │
│  - 不断循环直到得到答案                                           │
└────┬────────────────────────┬──────────────────────────────┬─────┘
     │                        │                              │
     ▼                        ▼                              ▼
 execute_python_code   MCP 工具函数                    其他工具
 (Python 代码执行)   (list_nutrition_foods,        (系统扩展点)
                      query_meals,
                      create_order ...)
                        │
                        ▼
               ┌──────────────────────┐
               │   mcp_client.py      │
               │  McpClient Class     │
               │                      │
               │ HTTP POST 请求       │
               │ {base_url}/tools/... │
               │ Header: Bearer token │
               └──────────┬───────────┘
                          │
                          ▼
              ┌──────────────────────────┐
              │ 麦当劳 MCP Server (远程)  │
              │ - 查询菜单 / 价格        │
              │ - 创建订单 / 查询订单    │
              │ - 管理优惠券 / 积分      │
              │ - 门店和地址管理         │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │  JSON 响应结果            │
              │  {code, data}            │
              └──────────┬───────────────┘
                         │
                    ┌────┴────┐
                    ▼         ▼
            向用户返回   保存会话
            (流式)     记忆
```

### 3.2 分层设计

| 层级 | 文件 | 职责 |
|------|------|------|
| **应用层** | `main.py` | Agent 创建、工具注册、请求处理 |
| **工具层** | `mcp_client.py` | 20 个 MCP 工具函数、客户端类 |
| **通信层** | HTTP POST | 与麦当劳 MCP Server 通信 |
| **数据层** | MCP Server | 菜单、订单、用户账户数据库 |

---

## 4. 技术栈

### 核心框架
- **AgentScope 1.0.11**：AI Agent 开发框架
- **AgentScope Runtime 1.0.5**：运行时环境和 HTTP 服务
- **FastAPI / Uvicorn**：Web 服务框架

### AI 模型
- **DashScope (阿里云百炼)**：大语言模型（Qwen 系列）
- **ReActAgent**：推理执行 Agent（思考→工具→回答）

### 存储和会话
- **InMemoryStateService**：Agent 状态（纯内存）
- **InMemorySessionHistoryService**：对话历史（纯内存）
- ⚠️ 注意：重启后数据丢失，生产环境需替换为 Redis/数据库

### 配置管理
- **PyYAML**：配置文件解析
- **Environment Variables**：敏感信息注入（推荐）

---

## 5. 文件结构

```
modelstudio-agent-starter/
├── README_en.md                 # 英文说明
├── README_zh.md                 # 中文说明
├── TESTING.md                   # 测试指南（详细）
├── PROJECT.md                   # 本文件（项目摘要）
├── requirements.txt             # Python 依赖
├── setup.py                     # 打包配置
│
└── deploy_starter/              # 主应用目录
    ├── config.yml               # 配置文件（APP_NAME、MCP_SERVER_URL 等）
    ├── main.py                  # 核心应用入口（2 个关键函数）
    │                            #   - query_func(): 处理用户请求
    │                            #   - init_func(): 启动时初始化 MCP
    │
    └── mcp_client.py            # MCP 客户端封装
                                 #   - McpClient 类（HTTP 通信）
                                 #   - 20 个工具函数
                                 #   - init_mcp_client() 初始化函数
```

---

## 6. 核心组件详解

### 6.1 main.py 的两个关键函数

#### init_func() - 启动初始化

**什么时候调用？** 服务启动时（@agent_app.init）

**做什么？**
1. 创建并启动内存服务（StateService、SessionHistoryService）
2. 读取环境变量，初始化 MCP 客户端
3. 输出「MCP client initialized」日志

**关键代码段**：
```python
mcp_url = os.getenv("MCP_SERVER_URL")
mcp_token = os.getenv("MCP_TOKEN")
init_mcp_client(base_url=mcp_url, token=mcp_token, timeout=10)
```

#### query_func() - 请求处理

**什么时候调用？** 每次用户发消息时（@agent_app.query）

**做什么？**
1. 从请求提取 session_id、user_id
2. 恢复该会话的历史状态（上下文连续性）
3. 初始化 Toolkit，注册所有 MCP 工具
4. 创建 ReActAgent (Friday)，绑定模型、工具、记忆
5. 流式执行 Agent，逐步返回消息
6. 对话结束后保存新的状态

**关键参数**：
- `msgs`：本次用户消息
- `request.user_id`：用户唯一 ID（用于查询账户信息）
- `request.session_id`：会话 ID（用于多轮对话上下文）

### 6.2 mcp_client.py 的三大类别

#### McpClient 类 - HTTP 通信
- `__init__(base_url, token, timeout)`：初始化客户端
- `call_tool(tool_name, payload)`：通用工具调用方法
- `_build_headers()`：构建认证 headers

#### 工具包装函数 - 20 个函数

**查询类**（不需要 user_id）
- `query_meals(store_code)`：菜单
- `query_meal_detail(meal_code)`：套餐详情
- `list_nutrition_foods(food_name)`：营养信息
- `query_nearby_stores(lat, lng)`：附近门店
- `campaign_calendar()`：营销活动
- `now_time_info()`：当前时间

**用户账户类**（需要 user_id）
- `query_my_coupons(user_id)`：我的优惠券
- `query_my_account(user_id)`：我的积分
- `available_coupons(user_id)`：可领优惠券
- `auto_bind_coupons(user_id)`：一键领券

**地址和门店类**（需要 user_id）
- `delivery_query_addresses(user_id)`：已保存地址
- `delivery_create_address(user_id, address)`：新增地址
- `query_store_coupons(store_code, user_id)`：门店优惠券

**订单和支付类**（需要 user_id）
- `calculate_price(store_code, items, coupons)`：价格计算
- `create_order(...)`：创建订单
- `query_order(order_id, user_id)`：查询订单

**积分商城类**（需要 user_id）
- `mall_points_products()`：兑换商品列表
- `mall_product_detail(product_id)`：商品详情
- `mall_create_order(user_id, product_id)`：兑换下单

#### 全局初始化
- `init_mcp_client(base_url, token, timeout)`：初始化全局 mcp_client 变量
- `mcp_client: Optional[McpClient] = None`：全局变量，被所有工具函数使用

---

## 7. API 接口

### 7.1 主要端点

| 端点 | 方法 | 用途 | 认证 |
|------|------|------|------|
| `/health` | GET | 健康检查 | 否 |
| `/process` | POST | 同步聊天请求 | 否 |
| `/process/stream` | POST | 流式响应请求 | 否 |
| `/` | GET | 服务信息（JSON） | 否 |

### 7.2 /process 请求格式

**标准 OpenAI 兼容格式**：

```json
{
  "input": [
    {
      "role": "user",
      "type": "message",
      "content": [
        {
          "type": "text",
          "text": "用户消息"
        }
      ]
    }
  ],
  "session_id": "test-session-1",
  "user_id": "test-user-1",
  "stream": true
}
```

**关键字段**：
- `input[0].content[0].text`：用户输入
- `session_id`：会话 ID（保持多轮对话上下文）
- `user_id`：用户 ID（用于查询账户信息）
- `stream`：是否流式输出（可选，默认 true）

### 7.3 配置项 (config.yml)

| 配置项 | 默认值 | 说明 | 优先级 |
|--------|-------|------|--------|
| `MCP_SERVER_URL` | （空） | MCP Server 地址 | 环境变量 > 配置文件 |
| `MCP_TOKEN` | （空） | MCP Server Token | 环境变量 > 配置文件 |
| `MCP_TIMEOUT` | 10 | 超时时间（秒） | 环境变量 > 配置文件 |
| `DASHSCOPE_API_KEY` | （空） | 阿里云百炼 API Key | 环境变量 > 配置文件 |
| `DASHSCOPE_MODEL_NAME` | qwen-turbo | 模型名称 | 仅配置文件 |
| `HOST` | 127.0.0.1 | 本地监听地址 | 仅配置文件 |
| `PORT` | 8080 | 监听端口 | 仅配置文件 |
| `DEBUG` | false | 调试模式 | 仅配置文件 |
| `LOG_LEVEL` | INFO | 日志级别 | 仅配置文件 |

---

## 8. 核心设计原理

### 8.1 Agent 如何调用工具？

1. **注册**：在 query_func 中将工具函数加入 Toolkit
   ```python
   toolkit.register_tool_function(query_meals)
   toolkit.register_tool_function(query_order)
   ```

2. **告知**：在 sys_prompt 中强制指导
   ```
   "所有菜单、价格、订单信息必须通过 MCP 工具查询，禁止编造"
   ```

3. **执行**：Agent 在 ReAct 推理循环中自动决定是否调用
   ```
   思考 → 识别需要查询菜单 → 调用 query_meals() 
   → 收到结果 → 继续推理 → 回答用户
   ```

### 8.2 用户身份管理

| 信息 | 来源 | 用途 |
|------|------|------|
| `user_id` | 请求体 | 查询用户的优惠券、积分、订单 |
| `session_id` | 请求体 | 保持多轮对话的上下文（共享记忆） |

**例子**：
- user_id="user-001" 的用户在多个 session 中对话，都能看到自己的优惠券和订单
- session_id="session-A" 的对话历史独立于 session_id="session-B"

### 8.3 MCP 工具何时需要 user_id？

**需要 user_id**（与用户账户相关）：
- query_my_coupons / query_my_account（个人数据）
- delivery_query_addresses / delivery_create_address（个人地址）
- query_store_coupons / create_order / query_order（与用户订单相关）

**不需要 user_id**（公开数据）：
- query_meals / query_meal_detail / list_nutrition_foods（菜单）
- query_nearby_stores（门店）
- campaign_calendar（活动）
- now_time_info（系统时间）

---

## 9. 扩展点和定制

### 9.1 增加新工具

**步骤 1**：在 mcp_client.py 中添加工具函数
```python
def my_custom_tool(param1: str) -> str:
    """新工具说明"""
    payload = {"param1": param1}
    result = mcp_client.call_tool("my-custom-tool", payload)
    return str(result)
```

**步骤 2**：在 main.py 的 query_func 中注册工具
```python
toolkit.register_tool_function(my_custom_tool)
```

**步骤 3**：在 sys_prompt 中说明工具的使用场景（可选但推荐）

### 9.2 修改 Agent 行为

**修改 sys_prompt**（main.py 中的 agent = ReActAgent(sys_prompt=...)）：
- 改变 Agent 的人格和说话风格
- 添加或移除某些工具的使用指导
- 强化或放松"必须使用工具"的要求

**修改模型配置**（main.py 中的 DashScopeChatModel）：
- 改换大模型（qwen-max / qwen-plus）
- 调整 temperature（影响回答的多样性）
- 启用/禁用思考链（enable_thinking）

### 9.3 替换存储层

默认使用内存存储（重启数据丢失）。生产环境需替换：

**替换 StateService**：
```python
# 当前（内存）
self.state_service = InMemoryStateService()

# 生产（Redis 示例）
self.state_service = RedisStateService(redis_host="...", redis_port=6379)
```

**替换 SessionHistoryService**：
```python
# 当前（内存）
self.session_service = InMemorySessionHistoryService()

# 生产（数据库示例）
self.session_service = DatabaseSessionHistoryService(db_url="...")
```

---

## 10. 测试和验证

### 10.1 快速验证清单

- [ ] 服务启动成功（`Service started`）
- [ ] 健康检查返回 "OK"（`curl /health`）
- [ ] MCP 客户端初始化成功（日志中有 MCP client initialized）
- [ ] 能接收简单聊天请求（不涉及 MCP 工具）
- [ ] Agent 自动调用 MCP 工具（日志中有 MCP tool called successfully）
- [ ] 多轮对话保持上下文（同 session_id 重复消息 Agent 能记住）
- [ ] 不同用户数据隔离（不同 user_id 无法看到彼此的数据）

### 10.2 常见问题排查

| 问题 | 原因 | 解决 |
|------|------|------|
| Agent 不调用工具 | MCP 配置错误或未配置 | 检查 MCP_SERVER_URL 和 MCP_TOKEN |
| 模块导入失败 | 相对导入路径问题 | 在 deploy_starter 目录下运行或用 python -m |
| 响应为空或很慢 | MCP Server 无响应或超时 | 增加 MCP_TIMEOUT，检查网络连接 |
| 乱码问题 | 配置文件编码 | 已修复为 UTF-8（open(..., encoding="utf-8")) |

### 10.3 测试工具

- **curl**：快速命令行测试
- **Postman**：可视化测试、请求管理、环境变量
- **TESTING.md**：完整的 6 个测试用例

---

## 11. 关键指标和性能

### 11.1 响应时间

| 场景 | 耗时 |
|------|------|
| Agent 不调用工具（直接回答） | 2-5 秒（取决于模型） |
| Agent 调用 1 个 MCP 工具 | 3-8 秒（包括网络往返） |
| Agent 调用 2 个工具（顺序） | 6-15 秒 |
| 流式输出(stream=true) | 首 token 1-2 秒，后续 0.1-0.5 秒/token |

### 11.2 资源占用

- **内存**：每个会话（session）约 50-500 KB（取决于对话长度）
- **CPU**：空闲时很低，等待 Agent 推理时 CPU 会升高
- **网络**：每次 MCP 调用 1-2 KB payload，响应 5-50 KB

---

## 12. 安全建议

- ✅ **敏感信息**：MCP_TOKEN、DASHSCOPE_API_KEY 必须通过环境变量注入，**不要写入代码和仓库**
- ✅ **用户数据**：MCP Server 侧需验证 user_id，防止用户越权访问他人数据
- ✅ **输入验证**：在调用 MCP 前验证用户输入（当前框架未实现，生产环境需补充）
- ✅ **限流**：生产环境需在网关或应用层实现限流，防止滥用
- ✅ **日志脱敏**：生产环境需脱敏日志中的敏感信息（优惠券 ID、订单号等）

---

## 13. 下一步和改进方向

### 近期（1-2 周）
- [ ] 编写前端聊天页面（调用 /process 或 /process/stream）
- [ ] 集成用户登录系统（获取 user_id）
- [ ] 添加输入校验和错误处理
- [ ] 性能测试和优化

### 中期（1-3 个月）
- [ ] 替换为 Redis/数据库存储（支持分布式部署）
- [ ] 添加收费机制和配额管理
- [ ] 集成支付系统（完成真实下单）
- [ ] 多语言支持（目前仅中文）
- [ ] 增加更多工具（积分查询、会员等级、推荐算法等）

### 长期（3-6 个月）
- [ ] 接入真实麦当劳业务系统（而不是 MCP 模拟）
- [ ] 微信/支付宝小程序集成
- [ ] Agent 能力提升（多模态、图片识别等）
- [ ] 用户行为分析和个性化推荐

---

## 14. 相关文档

| 文档 | 用途 |
|------|------|
| [README_zh.md](README_zh.md) | 项目简介、安装、使用 |
| [TESTING.md](TESTING.md) | 详细的测试指南和 6 个用例 |
| [PROJECT.md](PROJECT.md) | 本文件（项目摘要） |
| [config.yml](deploy_starter/config.yml) | 配置文件（带详细注释） |

---

## 15. 快速参考

### 启动服务
```bash
cd deploy_starter
python main.py
```

### 测试聊天
```powershell
$body = @{
    input = @(@{role="user"; type="message"; content=@(@{type="text"; text="你好，帮我查菜单"})})
    session_id = "test-1"
    user_id = "test-1"
} | ConvertTo-Json -Depth 10

curl -X POST http://127.0.0.1:8080/process -H "Content-Type: application/json" -d $body
```

### 配置 MCP
```powershell
$env:MCP_SERVER_URL = "https://mcp.mcd.cn"
$env:MCP_TOKEN = "your-token"
```

### 查看日志
在服务启动窗口直接查看，或修改 `config.yml` 的 `LOG_LEVEL: DEBUG` 获得详细日志。

---

**最后更新**：2026-04-12  
**维护者**：BridgeX Team  
**版本**：0.1.0
