# 本地测试说明

## 1. 前提条件

- 已安装 Python 3.10 及以上
- 已安装项目依赖：
  ```bash
  pip install -r requirements.txt
  ```
- 已准备好麦当劳 MCP Server 的 `base_url` 和 `token`
- 当前工作目录可以是项目根目录，也可以是 `deploy_starter` 目录

## 2. 配置 MCP 环境变量

建议通过环境变量注入 MCP 配置，避免把敏感信息写入仓库：

Windows PowerShell:
```powershell
$env:MCP_SERVER_URL = "https://your-mcp-server-url"
$env:MCP_TOKEN = "your-mcp-token"
$env:MCP_TIMEOUT = "10"
```

Linux / macOS:
```bash
export MCP_SERVER_URL="https://your-mcp-server-url"
export MCP_TOKEN="your-mcp-token"
export MCP_TIMEOUT="10"
```

## 3. 启动服务

在项目根目录下启动：
```bash
cd deploy_starter
$env:DASHSCOPE_API_KEY="你的key"
python main.py
```

如果你希望以包方式启动，运行：
```bash
cd ..
python -m deploy_starter.main
```

正常启动后会看到类似：
```text
Service started, press Ctrl+C to stop...
```

## 4. 验证服务是否在线

使用浏览器或 curl 访问健康检查接口：

```bash
curl http://127.0.0.1:8080/health
```

期望返回：
```text
OK
```

访问根路径 `/`，可以看到服务信息 JSON：

```json
{"service":"AgentScope Runtime","mode":"daemon_thread","endpoints":{"process":"/process","stream":"/process/stream","health":"/health"}}
```

这表示服务已启动，但根路径不是聊天页面。

## 5. 发送聊天请求（测试 Agent 和 MCP 工具调用）

### 5.1 请求格式说明

接口地址：`POST /process`

**请求格式（标准 OpenAI 兼容格式）：**

```json
{
  "input": [
    {
      "role": "user",
      "type": "message",
      "content": [
        {
          "type": "text",
          "text": "你好，帮我查一下麦当劳菜单"
        }
      ]
    }
  ],
  "session_id": "test-session",
  "user_id": "test-user"
}
```

**字段解释：**

| 字段 | 类型 | 是否必需 | 含义 | 示例 |
|------|------|--------|------|------|
| `input` | Array(Message) | ✅ 是 | 消息数组，包含本次对话的消息 | 见下方详解 |
| `input[0].role` | String | ✅ 是 | 消息发送者角色，通常为 "user" | "user" |
| `input[0].type` | String | ✅ 是 | 消息类型，固定值 "message" | "message" |
| `input[0].content` | Array(ContentBlock) | ✅ 是 | 内容块数组，可包含文本、图片等 | 见下方详解 |
| `input[0].content[0].type` | String | ✅ 是 | 内容块类型，当前仅支持 "text" | "text" |
| `input[0].content[0].text` | String | ✅ 是 | 文本内容 | "你好，帮我查一下麦当劳菜单" |
| `session_id` | String | ✅ 是 | 会话 ID，用于追踪多轮对话的上下文 | "test-session" |
| `user_id` | String | ✅ 是 | 用户 ID，用于隔离不同用户的数据 | "test-user" |
| `stream` | Boolean | 否 | 是否流式输出，默认为 true | true |

**为什么这样设计？**

- **OpenAI 兼容格式**：使用行业标准格式，便于迁移和集成，与 OpenAI API 兼容
- **Array 而非单一 message**：支持一次发送多条历史消息，便于上下文恢复
- **role/type/content 三层结构**：清晰区分消息来源、类型和内容，支持将来扩展（如图片、音频）
- **session_id + user_id**：允许系统管理多个用户的多个会话，隔离数据，支持会话持久化

### 5.2 发送聊天请求示例

**PowerShell 单行命令（推荐用于快速测试）：**

```powershell
curl -X POST http://127.0.0.1:8080/process -H "Content-Type: application/json" -d "{\"input\":[{\"role\":\"user\",\"type\":\"message\",\"content\":[{\"type\":\"text\",\"text\":\"你好，帮我查一下麦当劳菜单\"}]}],\"session_id\":\"test-session-1\",\"user_id\":\"test-user-1\"}"
```

**PowerShell 多行命令（推荐用于查看格式）：**

```powershell
$body = @{
    input = @(
        @{
            role = "user"
            type = "message"
            content = @(
                @{
                    type = "text"
                    text = "你好,我在这里：纬度31.0299，经度121.4312，帮我找附近门店"
                }
            )
        }
    )
    session_id = "test-session-1"
    user_id = "test-user-1"
} | ConvertTo-Json -Depth 10

curl -X POST http://127.0.0.1:8080/process `
  -H "Content-Type: application/json" `
  -d $body
```

**Linux/macOS bash 命令：**

```bash
curl -X POST http://127.0.0.1:8080/process \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      {
        "role": "user",
        "type": "message",
        "content": [
          {"type": "text", "text": "你好，帮我查一下麦当劳菜单"}
        ]
      }
    ],
    "session_id": "test-session-1",
    "user_id": "test-user-1"
  }'
```

**期望响应（流式）：**

```text
data: {"role": "assistant", "content": "您的位置坐标是上海浦东，我来为您查询附近的麦当劳门店..."}
data: {"role": "assistant", "content": "以下是您附近的门店列表..."}
data: [DONE]
```

## 常见问题及解决方案

### 问题：工具调用返回错误 "The tool function must return a ToolResponse object"

**原因**：工具函数的返回类型不符合 AgentScope 框架要求。

**解决方案**：已在 `mcp_client.py` 中更新所有工具函数：
- 导入 `ToolResponse` 类：`from agentscope.service import ToolResponse`
- 所有工具函数现在返回 `ToolResponse` 对象而不是 `str`
- 新增辅助函数 `_wrap_tool_result()` 用于格式转换

**验证方法**：
1. 检查 `mcp_client.py` 的第一个工具函数 `list_nutrition_foods`，应返回 `ToolResponse`
2. 运行智能体，查看是否能正常调用工具并获得完整响应

---

## 6. 详细测试 MCP 工具调用

### 6.1 工作原理

Agent 会根据用户消息和 sys_prompt 的指导，自动决定是否调用 MCP 工具。当 Agent 需要以下信息时，会自动触发工具调用：

1. **菜单和食品信息** → 调用 `query-meals`、`query-meal-detail`、`list-nutrition-foods`
2. **门店信息** → 调用 `query-nearby-stores`
3. **价格计算** → 调用 `calculate-price`
4. **下单** → 调用 `create-order`、`query-order`
5. **优惠券和积分** → 调用 `query-my-coupons`、`query-my-account` 等

### 6.2 测试用例 1：查询附近门店

**场景**：用户想查询附近有哪些麦当劳门店

**请求：**

```powershell
$body = @{
    input = @(
        @{
            role = "user"
            type = "message"
            content = @(
                @{
                    type = "text"
                    text = "我在北京西直门，请帮我查询附近的麦当劳门店"
                }
            )
        }
    )
    session_id = "test-session-2"
    user_id = "test-user-2"
} | ConvertTo-Json -Depth 10

curl -X POST http://127.0.0.1:8080/process -H "Content-Type: application/json" -d $body
```

**预期行为：**

1. Agent 识别出用户要查询附近门店
2. Agent 自动调用 `query_nearby_stores(latitude=39.93, longitude=116.37)` 工具
3. MCP Server 返回附近门店列表
4. Agent 将结果整理后返回给用户

**预期响应示例：**

```json
{
  "role": "assistant",
  "content": "西直门附近有以下麦当劳门店：\n1. 西直门餐厅（距离 0.2 km，营业时间 06:00-23:00）\n2. 中关村餐厅（距离 1.5 km，营业时间 06:30-23:30）\n..."
}
```

**格式含义：**
- `latitude` / `longitude`：根据地址名（西直门）推导的坐标
- Agent 自动计算或从用户输入中推断地理信息，无需人工指定坐标值

---

### 6.3 测试用例 2：查询菜单和价格

**场景**：用户想查询某门店的菜单，并了解具体价格

**请求：**

```powershell
$body = @{
    input = @(
        @{
            role = "user"
            type = "message"
            content = @(
                @{
                    type = "text"
                    text = "西直门店有什么汉堡？价格多少？"
                }
            )
        }
    )
    session_id = "test-session-2"  # 与上一条相同，保持会话连续性
    user_id = "test-user-2"
} | ConvertTo-Json -Depth 10

curl -X POST http://127.0.0.1:8080/process -H "Content-Type: application/json" -d $body
```

**预期行为：**

1. Agent 从前一轮对话的上下文中知道「西直门店」对应的门店代码（比如 MD_BJ_001）
2. Agent 调用 `query_meals(store_code="MD_BJ_001")` 获取菜单
3. Agent 调用 `query_meal_detail(meal_code="001")` 获取具体汉堡的详情
4. 返回菜单和价格信息

**预期响应示例：**

```json
{
  "role": "assistant",
  "content": "西直门店的汉堡有：\n- 巨无霸（¥25.99）：2 块牛肉饼、生菜、番茄酱\n- 麦香鸡（¥15.99）：脆皮炸鸡腿堡\n- 四川辣翅堡（¥18.99）：辣汁鸡翅堡\n..."
}
```

**格式含义：**
- `session_id` 相同：保持多轮对话的上下文连续性
- Agent 无需再问「你说的西直门店在哪儿」，因为前一轮已取得门店信息

---

### 6.4 测试用例 3：营养信息查询

**场景**：用户想了解某个汉堡的营养信息

**请求：**

```powershell
$body = @{
    input = @(
        @{
            role = "user"
            type = "message"
            content = @(
                @{
                    type = "text"
                    text = "巨无霸有多少卡路里？营养成分如何？"
                }
            )
        }
    )
    session_id = "test-session-2"
    user_id = "test-user-2"
} | ConvertTo-Json -Depth 10

curl -X POST http://127.0.0.1:8080/process -H "Content-Type: application/json" -d $body
```

**预期行为：**

1. Agent 识别出「巨无霸」是之前提到的菜品
2. Agent 调用 `list_nutrition_foods(food_name="巨无霸")` 获取营养信息
3. 返回详细的营养成分

**预期响应示例：**

```json
{
  "role": "assistant",
  "content": "巨无霸的营养信息：\n- 能量：563 kcal\n- 蛋白质：26g\n- 脂肪：28g\n- 碳水化合物：45g\n- 钠：873mg\n- 钙：200mg\n这是一份相对高热量但营养均衡的餐品。"
}
```

---

### 6.5 测试用例 4：模拟下单流程

**场景**：用户想下单，体验完整的订单流程

**第 1 步：用户表达点餐意向**

```powershell
$body = @{
    input = @(
        @{
            role = "user"
            type = "message"
            content = @(
                @{
                    type = "text"
                    text = "我想要 1 份巨无霸和 1 份薯条，外送到我在西直门的地址"
                }
            )
        }
    )
    session_id = "test-session-3"
    user_id = "test-user-3"
} | ConvertTo-Json -Depth 10

curl -X POST http://127.0.0.1:8080/process -H "Content-Type: application/json" -d $body
```

**预期行为：**

1. Agent 识别出用户要点的商品
2. Agent 调用 `calculate_price()` 计算总价
3. Agent 询问用户是否确认，或获取配送地址等信息

**第 2 步：用户确认订单**

```powershell
$body = @{
    input = @(
        @{
            role = "user"
            type = "message"
            content = @(
                @{
                    type = "text"
                    text = "确认，请帮我下单"
                }
            )
        }
    )
    session_id = "test-session-3"  # 同一会话
    user_id = "test-user-3"
} | ConvertTo-Json -Depth 10

curl -X POST http://127.0.0.1:8080/process -H "Content-Type: application/json" -d $body
```

**预期行为：**

1. Agent 调用 `create_order()` 创建订单
2. MCP Server 返回订单编号和支付链接
3. Agent 返回订单确认信息

**预期响应示例：**

```json
{
  "role": "assistant",
  "content": "订单已成功创建！\n订单号：ORD-20260412-001\n总价：¥68.99（包括配送费 ¥8）\n配送地址：北京市西城区西直门外大街\n预计配送时间：30-40 分钟\n\n请点击以下链接完成支付：https://pay.mcd.cn/ORD-20260412-001"
}
```

---

### 6.6 测试用例 5：查询已有订单

**场景**：用户想查询之前的订单状态

**请求：**

```powershell
$body = @{
    input = @(
        @{
            role = "user"
            type = "message"
            content = @(
                @{
                    type = "text"
                    text = "我想查查我上次的订单 ORD-20260412-001 进度如何了"
                }
            )
        }
    )
    session_id = "test-session-4"
    user_id = "test-user-3"  # 同一用户
} | ConvertTo-Json -Depth 10

curl -X POST http://127.0.0.1:8080/process -H "Content-Type: application/json" -d $body
```

**预期行为：**

1. Agent 识别出订单号
2. Agent 调用 `query_order(order_id="ORD-20260412-001", user_id="test-user-3")` 查询订单
3. 返回订单状态、预计配送时间等

**预期响应示例：**

```json
{
  "role": "assistant",
  "content": "订单 ORD-20260412-001 的状态：\n- 订单状态：配送中\n- 配送员：王师傅（优先骑手）\n- 配送员电话：138XXXX5678\n- 预计送达时间：14:25\n- 当前位置：距离你 2.3 km\n你可以实时跟踪订单。"
}
```

---

### 6.7 测试用例 6：优惠券和会员权益

**场景**：用户想查询有哪些优惠券可用

**请求：**

```powershell
$body = @{
    input = @(
        @{
            role = "user"
            type = "message"
            content = @(
                @{
                    type = "text"
                    text = "我有什么优惠券可以用？帮我看看最近有什么活动"
                }
            )
        }
    )
    session_id = "test-session-5"
    user_id = "test-user-3"
} | ConvertTo-Json -Depth 10

curl -X POST http://127.0.0.1:8080/process -H "Content-Type: application/json" -d $body
```

**预期行为：**

1. Agent 调用 `query_my_coupons(user_id="test-user-3")` 查询用户优惠券
2. Agent 调用 `campaign_calendar()` 查询最近活动
3. 返回可用优惠券列表和活动信息

**预期响应示例：**

```json
{
  "role": "assistant",
  "content": "你的可用优惠券：\n1. 满 50 减 10（有效期至 2026-04-30）\n2. 巨无霸 8 折（有效期至 2026-04-20）\n3. 套餐加赠小薯（有效期至 2026-04-25）\n\n最近活动：\n- 麦麦随心选（每日 11-14 点特惠）\n- 积分双倍日（本周五）\n您可以组合使用优惠券以获得最大优惠。"
}
```

---

### 6.8 监看工具调用的日志

要查看 Agent 实际调用了哪些工具，可以查看服务启动窗口的日志输出：

```text
DEBUG:root:MCP tool 'query-nearby-stores' called successfully: {...}
DEBUG:root:MCP tool 'query-meals' called successfully: {...}
...
```

或者在 `config.yml` 中改为 `LOG_LEVEL: "DEBUG"` 来看详细日志。

## 7. 排查 MCP 工具调用失败

### 7.1 问题：Agent 不调用工具，而是凭空编造答案

**原因排查：**

1. 检查 `MCP_SERVER_URL` 和 `MCP_TOKEN` 是否正确设置
2. 检查 MCP Server 是否在线（`curl {MCP_SERVER_URL}/health`）
3. 查看 `config.yml` 中的 `LOG_LEVEL` 是否为 `DEBUG`，如果不是，改为 DEBUG 重启看详细日志
4. 检查 `sys_prompt` 是否包含「必须使用工具」的指导语句

**解决办法：**

强化 sys_prompt，明确告诉 Agent：
```
"所有关于菜单、价格、订单、门店信息等数据必须通过调用 MCP 工具获取，禁止凭空生成。"
```

---

### 7.2 问题：收到 MCP Server 连接错误

**错误信息：** `麦当劳 MCP 调用失败：...`

**原因排查：**

1. **网络连接问题**
   ```powershell
   ping {MCP_SERVER_URL}  # 检查是否能 ping 通
   ```

2. **Token 错误**
   - 确认 `$env:MCP_TOKEN` 值正确
   - Token 不要包含多余空格或引号

3. **URL 格式错误**
   - 确保 URL 包含协议（https:// 或 http://）
   - 不要在末尾加 `/`，系统会自动补充

4. **超时**
   - 检查 MCP Server 响应是否很慢
   - 可调整 `MCP_TIMEOUT` 环境变量（单位：秒）

---

## 8. 完整测试清单

- [ ] 服务启动无错误
- [ ] 健康检查接口返回 "OK"
- [ ] 能接收简单问答（不涉及 MCP 工具的）
- [ ] Agent 自动调用查询门店工具
- [ ] Agent 自动调用查询菜单工具
- [ ] Agent 自动调用价格计算工具
- [ ] 多轮对话保持上下文连续性（同一 session_id）
- [ ] 不同用户数据隔离（不同 user_id）
- [ ] MCP 工具返回的数据被 Agent 正确使用和展示
- [ ] 流式输出正常工作（`/process/stream` 端点）

## 9. 使用 Postman 测试（推荐）

相比 curl，Postman 更易管理请求和查看响应：

1. 在 Postman 中创建 POST 请求
2. URL：`http://127.0.0.1:8080/process`
3. Headers：
   ```
   Content-Type: application/json
   ```
4. Body（raw JSON）：复制上面的请求体示例
5. 点击 Send，观察响应
6. 可在 Postman 中保存请求模板，便于反复测试

## 10. 进一步测试建议

- 开发简单的前端页面，调用 `/process` 或 `/process/stream` 实现网页聊天界面
- 使用压力测试工具（如 Apache Bench）测试并发性能
- 监控 MCP Server 的响应时间，优化超时配置
- 记录和分析 Agent 的工具调用序列，改进 sys_prompt 的指导文本

---

## 11. 常见问题详解

### 11.1 问题一：如何使用 Postman 进行测试？

**步骤 1：下载并安装 Postman**

访问 https://www.postman.com/downloads/ 下载桌面版本。

**步骤 2：创建新请求**

1. 打开 Postman，点击左上角 "+" 按钮或 "New" → "Request"
2. 给请求命名，比如 "麦当劳聊天请求"
3. 选择保存到集合（可创建新集合如 "McDonald's Tests"）

**步骤 3：配置请求**

| 配置项 | 值 |
|--------|-----|
| 请求方法 | POST |
| 请求地址 | http://127.0.0.1:8080/process |

**步骤 4：设置 Headers**

点击 "Headers" 选项卡，添加：

| Key | Value |
|-----|-------|
| Content-Type | application/json |

**步骤 5：设置 Body**

1. 点击 "Body" 选项卡
2. 选择 "raw" 单选按钮
3. 从右侧下拉菜单选择 "JSON"
4. 在文本框中粘贴以下完整请求体：

```json
{
  "input": [
    {
      "role": "user",
      "type": "message",
      "content": [
        {
          "type": "text",
          "text": "我在北京西直门，帮我查附近的麦当劳门店"
        }
      ]
    }
  ],
  "session_id": "postman-test-session-1",
  "user_id": "postman-test-user-1"
}
```

**步骤 6：发送请求**

点击蓝色 "Send" 按钮，Postman 会将请求发送到服务器。

**步骤 7：查看响应**

响应会在下方显示，分为多个选项卡：
- **Body**：响应内容（通常是 JSON）
- **Status**：HTTP 状态码（200 = 成功）
- **Time**：响应时间（毫秒）
- **Size**：响应大小（字节）

**步骤 8：保存多个测试用例**

在同一个请求中，修改 Body 的内容，然后多次发送，观察不同输入的响应：

```json
{
  "input": [
    {
      "role": "user",
      "type": "message",
      "content": [
        {
          "type": "text",
          "text": "巨无霸多少钱？"
        }
      ]
    }
  ],
  "session_id": "postman-test-session-1",  # 保持相同以维持对话上下文
  "user_id": "postman-test-user-1"
}
```

**Postman 相比 curl 的优势：**

| 对比项 | curl | Postman |
|--------|------|---------|
| 学习曲线 | 陡峭 | 平缓 |
| 界面 | 命令行 | 图形化 |
| 保存历史 | 需手动编写脚本 | 自动保存 |
| 响应格式化 | 需额外工具 | 自动格式化和高亮 |
| 集合管理 | 不支持 | 支持（分组、共享） |
| 环境变量 | 需手动替换 | 内置环境变量管理 |
| 预请求脚本 | 不支持 | 支持（自动化测试） |

---

### 11.2 问题二：智能体如何获得用户位置？

**当前实现方式：用户主动表述位置**

目前 Agent 无法自动获取用户的 GPS 位置。位置信息需要通过以下方式获得：

#### 方式 1：用户在消息中主动说明

**用户输入：**
```
我在北京西直门，帮我查附近的麦当劳
```

**Agent 处理流程：**
1. Agent 从文本中识别出地名「北京西直门」
2. Agent 通过内置的地理编码功能或调用地图 API 将地名转换为坐标
3. Agent 调用 `query_nearby_stores(latitude=39.93, longitude=116.37)`
4. MCP Server 返回附近门店列表

**优点：** 简单直接，用户友好  
**缺点：** 需要用户主动提供

#### 方式 2：通过请求参数传递位置（推荐用于 App 集成）

如果是 App 或网页集成，可以在请求中直接包含地理信息：

**修改后的请求体（扩展格式）：**

```json
{
  "input": [
    {
      "role": "user",
      "type": "message",
      "content": [
        {
          "type": "text",
          "text": "帮我查附近的麦当劳"
        }
      ]
    }
  ],
  "session_id": "mobile-app-session-1",
  "user_id": "mobile-user-001",
  "location": {
    "latitude": 39.93,
    "longitude": 116.37,
    "address": "北京西直门"
  }
}
```

**需要修改的代码：**

1. 在 `main.py` 的 `query_func` 中接收 location 参数
2. 在 sys_prompt 中告诉 Agent「如果用户没有说明位置，检查是否有 location 参数」
3. 将 location 传给 Agent 的上下文

**示例修改（main.py）：**

```python
async def query_func(
    self,
    msgs,
    request: AgentRequest = None,
    location: dict = None,  # 新增参数
    **kwargs,
):
    # ... 现有代码 ...
    
    # 如果有位置信息，可存储在 Agent 的上下文中
    agent_context = {
        "user_location": location,
        "default_coordinates": (location["latitude"], location["longitude"]) if location else None
    }
    
    # 将上下文传给 Agent（具体方式取决于 AgentScope 框架）
```

#### 方式 3：集成地理位置服务（高级）

如果要完全自动化，可以集成第三方地理定位服务：

1. **浏览器 API（Web 端）**
   - 使用 `navigator.geolocation.getCurrentPosition()` 获取用户位置
   - 需要用户授权

2. **移动 App 集成**
   - 使用 Android/iOS 原生 API 获取 GPS 位置
   - 在发送请求时自动包含 location 参数

3. **IP 地址定位（低精度）**
   - 从请求的 IP 地址推断大致位置
   - 精度不高，仅用于备选方案

**推荐方案：**
- **Web 聊天页面**：主动向用户询问「允许我获取你的位置吗？」，收到同意后使用浏览器 API
- **移动 App**：在 App 后台获取位置，随请求一并发送
- **简单方案**：让用户在首次对话时说一遍位置，存储在 session，后续对话自动使用

---

### 11.3 问题三：智能体如何知道用户的麦当劳账户（券、积分等）？

**当前实现方式：通过 user_id 查询麦当劳 MCP Server**

Agent 本身不存储用户账户信息，而是通过以下流程：

#### 工作原理

```
用户请求
   ↓
Request 包含 user_id = "user-123"
   ↓
Agent 识别需要查询用户信息
   ↓
Agent 调用 query_my_coupons(user_id="user-123")
   ↓
MCP Server 在其数据库中查询 user-123 的优惠券
   ↓
返回结果给 Agent
   ↓
Agent 返回给用户
```

#### 具体实现

**1. 请求中必须包含 user_id**

每个请求都需要一个有效的 user_id：

```json
{
  "input": [...],
  "session_id": "...",
  "user_id": "mcd-user-1001"  # ← 关键：麦当劳用户 ID
}
```

**user_id 的来源**：
- **自注册/登录系统**：用户在网页/App 上登录麦当劳账户后获得的用户 ID
- **第三方登录**：通过微信、支付宝等登录，获得对应的用户 ID
- **匿名用户**：如果是匿名聊天，可用临时 ID（但无法访问个人账户）

**2. MCP Server 侧需要支持账户查询**

MCP Server 必须实现以下工具（已有）：
- `query_my_coupons(user_id)` → 返回用户优惠券
- `query_my_account(user_id)` → 返回用户积分账户
- `query-store-coupons(store_code, user_id)` → 返回用户在该门店可用的券

**3. Agent 何时自动调用这些工具**

当用户说出以下关键词时，Agent 会自动调用：

| 用户输入 | 触发的工具 | 备注 |
|--------|---------|------|
| "我有什么优惠券" | query_my_coupons | 需要 user_id |
| "我的积分" | query_my_account | 需要 user_id |
| "我有多少钱" | query_my_account | 需要 user_id |
| "最近有什么活动" | campaign_calendar | 不需要 user_id |
| "在这家店能用什么券" | query_store_coupons | 需要 store_code 和 user_id |

#### 数据流示例

**场景**：用户问「我有什么优惠券」

**请求：**
```json
{
  "input": [
    {
      "role": "user",
      "type": "message",
      "content": [
        {"type": "text", "text": "我有什么优惠券可以用？"}
      ]
    }
  ],
  "session_id": "user-session-001",
  "user_id": "mcd-user-1001"  # ← 关键：这决定了查询谁的数据
}
```

**Agent 内部流程：**

1. Agent 读取 user_id = "mcd-user-1001"
2. Agent 识别出用户要查询优惠券
3. Agent 调用 `query_my_coupons(user_id="mcd-user-1001")`
4. MCP Server 数据库查询：获取 mcd-user-1001 拥有的所有优惠券
5. 返回结果（包含券号、金额、有效期等）
6. Agent 整理后返回给用户

**MCP Server 响应示例：**

```json
{
  "code": 0,
  "data": {
    "coupons": [
      {
        "coupon_id": "COUP-001",
        "name": "满 50 减 10",
        "discount_amount": 10,
        "applicable_items": ["汉堡", "套餐"],
        "expiry_date": "2026-05-30",
        "status": "available"
      },
      {
        "coupon_id": "COUP-002",
        "name": "巨无霸 8 折",
        "discount_rate": 0.2,
        "applicable_items": ["巨无霸"],
        "expiry_date": "2026-04-20",
        "status": "available"
      }
    ],
    "total_count": 2,
    "points": {
      "available": 523,
      "frozen": 50,
      "expiring_soon": 10
    }
  }
}
```

#### 实际应用中的注意事项

**1. 用户认证和授权**

```
Web/App → 用户登录 → 获取 access_token → 
获取 user_id → 发送请求时包含 user_id
```

例如（伪代码）：
```javascript
// App 登录
const loginResponse = await fetch('https://api.mcd.cn/login', {
  method: 'POST',
  body: JSON.stringify({ phone, password })
});
const { user_id, access_token } = await loginResponse.json();

// 存储 user_id，后续聊天请求时使用
$user_id = user_id;
```

**2. 隐私和数据安全**

- ✅ **正确做法**：用户只能看到自己的账户信息（通过 user_id 验证）
- ❌ **错误做法**：任意 user_id 都能查询任何用户的数据

MCP Server **必须在接收请求时验证 user_id 的有效性**，比如：

```python
def query_my_coupons(user_id: str) -> dict:
    # 验证 user_id 是否属于当前登录用户
    if not is_authorized(user_id):
        raise PermissionError("无权访问此用户的数据")
    
    # 查询数据库
    coupons = db.query_coupons(user_id)
    return coupons
```

**3. 跨会话数据同步**

由于 Agent 是无状态的，不同 session_id 的对话可能访问同一用户的数据：

```json
// Session 1
{
  "user_id": "mcd-001",
  "session_id": "session-A"
}

// Session 2（同一用户，新对话）
{
  "user_id": "mcd-001",
  "session_id": "session-B"
}
```

两个会话都能查询到 mcd-001 的优惠券和积分，这是正常的设计。

#### 总结

| 信息类型 | 获取方式 | 需要 user_id | Postman 测试方法 |
|--------|--------|-----------|---------|
| **优惠券** | query_my_coupons(user_id) | ✅ 是 | 在请求中填 user_id：user-123 |
| **积分账户** | query_my_account(user_id) | ✅ 是 | 在请求中填 user_id：user-123 |
| **门店优惠券** | query_store_coupons(store_code, user_id) | ✅ 是 | 同上，并提供 store_code |
| **营销活动** | campaign_calendar() | ❌ 否 | 不需要 user_id |
| **菜单信息** | query_meals(store_code) | ❌ 否 | 不需要 user_id |

**关键点**：Agent 本身不保存账户信息，所有账户数据都来自 MCP Server，通过 user_id 查询。
