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

## 5. 发送聊天请求

接口地址是 `/process`，示例请求：

```bash
curl -X POST http://127.0.0.1:8080/process \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，帮我查一下麦当劳菜单", "user_id": "test-user", "session_id": "test-session"}'
```

如果返回正常，则说明聊天接口可用。

## 6. 测试麦当劳 MCP 工具调用

1. 首先确保 MCP Server 地址和 token 正确。
2. 启动服务后发送一个对话请求，让 Agent 触发 MCP 查询，比如：
   - `帮我查询附近门店`
   - `帮我查一下该门店的菜单`
   - `这个汉堡多少卡路里`
3. 如果 MCP 工具调用成功，Agent 会返回真实查询结果。

如果需要手动测试具体工具，可以使用 `mcp_client.py` 中的函数接口。

## 7. 常见问题排查

- `ModuleNotFoundError: No module named 'deploy_starter'`
  - 请确认当前目录是 `deploy_starter`，或者使用 `python -m deploy_starter.main` 从项目根目录运行。

- `UnicodeDecodeError` 读取 `config.yml`
  - 已修复为使用 `encoding="utf-8"` 读取配置文件。

- 根路径 `/` 返回 JSON，而不是聊天页面
  - 这是正常行为，当前项目只提供 API 服务，不包含前端页面。

- `MCP 工具将不可用`
  - 请确认 `MCP_SERVER_URL` 和 `MCP_TOKEN` 已正确设置，并重启服务。

## 8. 进一步测试建议

- 使用 Postman / Insomnia 发送 `/process` 请求，观察返回内容
- 如果项目需要页面体验，可另行开发简单前端，调用 `/process` 或 `/process/stream`
- 通过 `user_id` 和 `session_id` 测试会话连续性，确认多轮对话功能正常
