# AGENTS.md — ModelStudio Agent Starter

> 面向 AI Coding Agent 的速查手册。修改代码前请先阅读本节，避免踩坑。
>
> ⚠️ **重要**：项目中的 `README.md`、`PROJECT.md`、`TESTING.md` 等文档存在**过期信息**，部分 shell 命令实际无法运行。请以**本文件和实际代码**为准。

---

## 1. 项目定位

基于 **FastAPI + AgentScope + DashScope** 的 ReAct 智能体服务（代号 Friday）。
核心场景：**跨商家智能点餐助手**，同时接入两套 MCP Server：
- **麦当劳 MCP**（真实业务数据，10 个工具，含优惠券体系）
- **星选汉堡 MCP**（虚拟竞品商家，6 个工具，无优惠券）

支持本地运行和阿里云百炼高代码云端部署。

---

## 2. 目录结构与关键文件

```
modelstudio-agent-starter/
├── deploy_starter/
│   ├── main.py              # 核心入口：Agent 创建、工具注册、请求处理、链路校验
│   ├── mcp_client.py        # 双 MCP 客户端封装：McpClient 类 + 16 个工具函数 + ToolCallTracker
│   ├── config.yml           # 全局配置（扁平 key:value，不支持嵌套）
│   └── test_mcp_init.py     # MCP 握手与工具调用单元测试
├── temp_mcp_framework/      # 本地虚拟 MCP Server（星选汉堡）
│   └── server_corrected.py  # 兼容 Streamable HTTP 的 FastAPI MCP Server
├── setup.py                 # 打包配置（但 entry_point 指向的 run_app 不存在，有 bug）
├── requirements.txt         # Python 依赖
├── PROJECT.md               # 项目摘要（架构图、分层设计、扩展点）—— 部分命令过期
├── TESTING.md               # 测试指南 —— 部分 curl 示例过期
└── README_zh.md / README_en.md  # 项目说明 —— 部分启动命令过期
```

**修改任何代码前，先定位到正确层级：**
- 改 Agent 行为 / 注册工具 → `main.py`
- 改 MCP 调用逻辑 / 新增工具 → `mcp_client.py`
- 改配置项 → `config.yml`（同时检查 `setup.py` 是否引用）

---

## 3. 编码规范与约束

### 3.1 Python 版本与依赖
- Python ≥ 3.10
- 核心依赖：`agentscope==1.0.11`、`agentscope-runtime==1.0.5`、`fastapi==0.116.1`
- 不允许引入与现有框架冲突的大版本升级

### 3.2 配置文件格式
`config.yml` 只支持**扁平** `key: value` 格式，**不支持嵌套 YAML**。解析器在 `main.py` 和 `setup.py` 中各有一份，实现一致：
```python
# 解析逻辑：按行读取，冒号分割，strip 引号，转 bool/int
```
- 若新增嵌套结构，需同时修改两个解析器 → **不推荐，保持扁平**
- 布尔值写 `true`/`false`（小写），字符串引号可选

### 3.3 工具函数返回类型
所有注册到 `Toolkit` 的工具函数**必须**返回 `agentscope.tool.ToolResponse` 对象，不能直接返回 `str` 或 `dict`。

```python
from agentscope.tool import ToolResponse
from agentscope.message import TextBlock

# ✅ 正确
return ToolResponse(content=[TextBlock(text="...")])

# ❌ 错误
return "..."
```

`mcp_client.py` 中的 `_wrap_tool_result()` 已封装三种 MCP 返回格式的转换，新增工具直接复用。

### 3.4 导入兼容性
`main.py` 对 `mcp_client` 做了**双重导入保护**（支持直接运行和模块运行）：
```python
try:
    from mcp_client import ...
except ModuleNotFoundError:
    from deploy_starter.mcp_client import ...
```
- 新增工具到 `mcp_client.py` 后，**必须**同步更新 `main.py` 中的两个导入块
- 新增工具后，**必须**在 `main.py` 的 `_build_toolkit()` 中 `register_tool_function(...)`

### 3.5 环境变量 > 配置文件
敏感配置（`DASHSCOPE_API_KEY`、`MCP_TOKEN`、`MCP_SERVER_URL` 等）优先从环境变量读取，回退到 `config.yml`。
- **禁止**在 `config.yml` 中填写真实密钥后提交到仓库
- 当前 `config.yml` 中 `MCP_TOKEN` 已有占位值，本地开发可用，但生产必须走环境变量

---

## 4. 启动方式（以实际代码为准）

### ❌ 已有文档中的错误命令

| 错误命令 | 来源 | 原因 |
|---------|------|------|
| `uvicorn deploy_starter.main:app --host ...` | README_zh.md / README_en.md | `main.py` 中没有名为 `app` 的变量；只有 `agent_app = AgentApp(...)`，是 AgentScope Runtime 实例，不是 FastAPI app，无法被 uvicorn 直接加载 |
| `pip install` 后运行 `ModelStudio-Agent-starter` | setup.py 定义的 entry_point | entry_point 指向 `deploy_starter.main:run_app`，但 `main.py` 中**不存在** `run_app` 函数 |
| `bash export DASHSCOPE_API_KEY=...` | README / PROJECT.md | 项目在 Windows 环境运行，应使用 PowerShell `$env:` 语法 |

### ✅ 实际可行的启动命令

**方式一：在项目根目录以模块方式启动（推荐）**
```powershell
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置环境变量（Windows PowerShell）
$env:DASHSCOPE_API_KEY="sk-xxx"
$env:MCP_SERVER_URL="https://mcp.mcd.cn"
$env:MCP_TOKEN="your-token"

# 3. 启动服务
python -m deploy_starter.main
```

**方式二：在 deploy_starter 目录内直接启动**
```powershell
cd deploy_starter
$env:DASHSCOPE_API_KEY="sk-xxx"
python main.py
```

**方式三：使用 uvicorn 启动（需暴露内部 FastAPI app）**
> 当前代码未将 FastAPI app 暴露为顶级变量，如需 uvicorn 启动，需修改 `main.py` 在模块级别导出 `app = agent_app._app`（或类似属性）。**不建议**，优先用方式一/二。

服务启动后会看到：
```text
✓ 麦当劳 MCP: https://mcp.mcd.cn
✓ 星选汉堡 MCP: https://...
Service started, press Ctrl+C to stop...
```

---

## 5. 常见修改场景指南

### 5.1 新增 MCP 工具

**Step 1** — 在 `mcp_client.py` 中新增包装函数：
```python
def my_new_tool(param: str) -> ToolResponse:
    """工具说明（Agent 会读 docstring 决定是否调用）"""
    try:
        payload = {"param": param}
        result = mcd_client.call_tool("my-new-tool", payload)
        return _wrap_tool_result("my-new-tool", result)
    except Exception as e:
        return ToolResponse(content=[TextBlock(text=str(e))])
```

**Step 2** — 在 `main.py` 的两个 `from mcp_client import (...)` 块中添加新工具名。

**Step 3** — 在 `main.py` 的 `_build_toolkit()` 中注册：
```python
toolkit.register_tool_function(my_new_tool)
```

**Step 4** — 在 `_SYS_PROMPT` 中补充工具的使用场景说明（可选但强烈建议）。

### 5.2 修改 Agent 人格 / 系统提示

直接编辑 `main.py` 中的 `_SYS_PROMPT` 字符串变量。
- 该 prompt **强制要求** Agent 使用工具获取业务数据，禁止编造
- 包含「门店名/地址必须与工具返回完全一致」的硬性规则
- 修改后需观察 Agent 是否仍遵守工具调用纪律

### 5.3 切换大模型或调整生成参数

在 `query_func()` 中修改 `DashScopeChatModel` 的参数：
```python
model=DashScopeChatModel(
    config.get("DASHSCOPE_MODEL_NAME"),   # 可在 config.yml 修改
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    enable_thinking=True,                  # 思考链开关
    stream=True,
    generate_args={"temperature": config.get("LLM_TEMPERATURE", 0.1)},
),
```
- `enable_thinking=True` 会增加 Token 消耗，但提升工具调用准确率
- `temperature` 默认 0.1，工具调用场景不建议高于 0.3

### 5.4 替换存储层（生产必做）

当前使用纯内存存储，重启后数据丢失：
```python
self.state_service = InMemoryStateService()
self.session_service = InMemorySessionHistoryService()
```

替换示例（需安装对应依赖）：
```python
# from agentscope_runtime.engine.services.agent_state import RedisStateService
# from agentscope_runtime.engine.services.session_history import RedisSessionHistoryService
```

---

## 6. 已知陷阱与注意事项

| 陷阱 | 说明 | 规避方法 |
|------|------|---------|
| **已有文档中的启动命令失效** | README/PROJECT/TESTING 中部分命令无法直接运行（uvicorn app、bash export、entry_point 等） | 以本文件「启动方式」章节为准 |
| **ToolResponse 类型错误** | 工具函数返回 `str` 或 `dict` 会导致 AgentScope 抛出 `must return a ToolResponse object` | 所有工具函数通过 `_wrap_tool_result()` 包装 |
| **MCP 握手失败** | `McpClient` 初始化时会自动执行 JSON-RPC 握手（initialize → tools/list），任一环节失败则 `handshake_success=False`，后续工具调用抛异常 | 检查 `MCP_SERVER_URL` 和 `MCP_TOKEN`；查看启动日志中的 `✓/✗` 标记 |
| **工具链路校验失败触发重试** | `main.py` 在 `query_func` 中对每个请求最多重试 3 次。若回复含价格但未调用菜单工具，或门店名与工具返回不一致，会自动注入纠错指令并重试 | 观察日志 `[工具链路校验失败]`；若频繁触发，检查 sys_prompt 是否足够强 |
| **配置文件解析不支持嵌套** | `config.yml` 写 `a: {b: 1}` 会被解析成字符串 `"{b: 1}"` | 保持扁平结构；复杂配置用 JSON 字符串或改解析器 |
| **session 内存丢失** | 重启服务后所有对话历史和 Agent 状态消失 | 预期行为；生产环境替换 Redis/DB 存储 |
| **双导入块遗漏** | 只改了 `try` 块中的导入，没改 `except` 块 | 搜索 `from mcp_client import`，确保两处同步 |
| **星选汉堡与麦当劳格式差异** | 麦当劳 MCP 返回格式为 `{content:[{text:"..."}]}`，星选汉堡为 `{success:true, data:...}` | `_wrap_tool_result()` 已处理；新增第三方 MCP 需评估格式 |
| **sys_prompt 过长导致模型忽略尾部指令** | `_SYS_PROMPT` 已接近较长篇幅，新增规则建议放在「关键字段输出规则」附近 | 保持 prompt 结构清晰，用 `【】` 区块分隔 |

---

## 7. 本地开发与测试

### 7.1 快速启动
```powershell
pip install -r requirements.txt
$env:DASHSCOPE_API_KEY="sk-xxx"
$env:MCP_SERVER_URL="https://mcp.mcd.cn"
$env:MCP_TOKEN="your-token"
python -m deploy_starter.main
```

> 注意：项目中的 `README` 和 `TESTING.md` 混用了 bash 语法（`export` / `\` 换行），在 Windows PowerShell 上无法直接运行。以下所有命令均基于 **Windows PowerShell** 验证。

### 7.2 验证清单（每次修改后必做）

**1. 健康检查**
```powershell
curl http://127.0.0.1:8080/health
# 期望返回："OK"
```

**2. 发送聊天请求（PowerShell 多行命令，唯一稳定可用格式）**
```powershell
$body = @{
    input = @(
        @{
            role = "user"
            type = "message"
            content = @(
                @{
                    type = "text"
                    text = "你好，帮我查一下麦当劳菜单"
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

**3. 其他验证项**
- [ ] 启动无报错，日志显示 `Service started, press Ctrl+C to stop...`
- [ ] 启动日志中显示 `✓ 麦当劳 MCP` 和 `✓ 星选汉堡 MCP`（或至少一个可用）
- [ ] 发送涉及价格的请求，Agent **实际调用**菜单工具（查看日志中 `[ToolTracker] recorded: query_meals`）
- [ ] 同一 `session_id` 的多轮对话保持上下文
- [ ] 不同 `user_id` 的数据相互隔离

> ⚠️ **不要使用** `TESTING.md` 和 `README` 中的 bash 风格 curl（`\` 换行、单引号 JSON）或单行转义 JSON，这些命令在 Windows PowerShell 下会因 JSON 格式错误或转义问题而失败。

### 7.3 调试日志
在 `config.yml` 中设置 `LOG_LEVEL: DEBUG` 可获得：
- MCP 握手详情
- 工具调用记录（`[ToolTracker] recorded: ...`）
- 工具链路校验失败原因

---

## 8. 安全红线

- **禁止**将 `DASHSCOPE_API_KEY`、`MCP_TOKEN` 等敏感信息硬编码并提交到 Git
- `config.yml` 中的 `MCP_TOKEN` 在提交前必须清空或替换为占位符
- 生产环境必须关闭 `DEBUG: true`
- MCP Server 侧需自行校验 `user_id` 权限，防止水平越权（当前代码不处理鉴权）

---

## 9. 延伸阅读（注意甄别过期信息）

| 文档 | 内容 | 注意事项 |
|------|------|---------|
| `PROJECT.md` | 架构图、分层设计、API 接口详情 | 启动命令部分可能过期，以本文件为准 |
| `TESTING.md` | 测试用例与 curl 示例 | **5.2 章节 PowerShell 多行命令可用**，其余 bash 风格 curl（`\` 换行、单引号 JSON）及单行命令在 Windows PowerShell 上大多会因 JSON 格式错误而失败 |
| `README_zh.md` / `README_en.md` | 项目简介、部署文档 | **`uvicorn` 启动命令和 `export` 环境变量语法在 Windows 上无法直接运行** |
| `deploy_starter/config.yml` | 每个配置项的详细注释 | 配置项本身准确 |

---

**版本**：0.1.0  
**最后更新**：2026-04-21
