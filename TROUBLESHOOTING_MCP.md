# MCP API 调用 404 错误 - 完整故障排除指南

## 问题诊断

### 当前状态
- ✅ **网络连接**: 正常 (能连接到 mcp.mcd.cn)
- ✅ **协议**: JSON-RPC 2.0 (已确认)
- ✅ **API 端点**: POST https://mcp.mcd.cn/ (根路径)
- ❌ **工具调用**: 所有工具返回 "method not found" (-32601 错误)

### 根本问题
所配置的所有工具名称（listNutritionFoods, queryMeals, 等）都不被 MCP Server 识别。

---

## 可能的原因及解决方案

### 原因 1️⃣: Token 已过期

**症状**: Token 本身有效但无权访问工具

**解决方案**:
```bash
# 1. 重新获取 Token
# 从 MCP Server 管理员或认证系统获取新的 Token

# 2. 更新 config.yml
MCP_TOKEN: "new-token-here"

# 3. 或通过环境变量设置
export MCP_TOKEN="new-token-here"
```

---

### 原因 2️⃣: 工具名称完全不同

**症状**: 工具存在但名称格式不同

**解决方案**:
```
需要获取 MCP Server 的真实工具列表。常见方法：

1. 查看 MCP Server 的 API 文档
2. 查看 MCP Server 的源代码
3. 向 MCP Server 管理员咨询
4. 查看部署配置文件
```

**可能的文件**:
- `MCP Server 部署目录/config.json`
- `MCP Server 部署目录/tools/`
- `MCP Server 部署目录/README.md`

---

### 原因 3️⃣: 需要特殊的初始化步骤

**症状**: MCP Server 需要先调用某个初始化方法

**解决方案**:
```python
# 在 mcp_client.py 的 init_mcp_client 中添加初始化
def init_mcp_client(base_url: str, token: str, timeout: int = 10):
    global mcp_client
    mcp_client = McpClient(base_url=base_url, token=token, timeout=timeout)
    
    # 尝试初始化
    try:
        rpc_payload = {
            "jsonrpc": "2.0",
            "method": "initialize",  # 或其他初始化方法
            "params": {"token": token},
            "id": 1,
        }
        response = requests.post(base_url, json=rpc_payload)
        logger.info(f"MCP initialization: {response.json()}")
    except Exception as e:
        logger.warning(f"MCP initialization failed: {e}")
```

---

## 立即修复步骤

### Step 1: 获取工具列表

**选项 A - 联系管理员**:
```
向麦当劳 MCP Server 的维护团队询问：
- 支持的工具名称列表
- API 文档或规范
- 获取有效 Token 的方式
```

**选项 B - 查看服务器配置**:
```bash
# 在 MCP Server 部署目录查找配置文件
find /path/to/mcp-server -name "*.json" -o -name "*.yml" -o -name "*.yaml"

# 查找工具定义
ls /path/to/mcp-server/tools/
```

**选项 C - 添加日志调试**:
```python
# 在 mcp_client.py 中添加对每个 RPC 请求的详细日志
def call_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    rpc_payload = {
        "jsonrpc": "2.0",
        "method": tool_name,
        "params": payload,
        "id": 1,
    }
    
    print(f"DEBUG: Sending RPC request")
    print(f"  Method: {tool_name}")
    print(f"  Payload: {json.dumps(rpc_payload)}")
    
    response = requests.post(self.base_url, json=rpc_payload, ...)
    
    print(f"  Response: {response.text}")
    
    # ... rest of code
```

### Step 2: 尝试已知工具名称的变体

如果不能获取文档，可以用以下脚本尝试更多名称：

```bash
python find_tool_names.py
```

注：当前脚本已尝试了常见的 30+ 种名称格式，全部失败。

### Step 3: 查看现有配置

检查 config.yml 中 MCP 相关配置：
```yaml
MCP_SERVER_URL: "https://mcp.mcd.cn"
MCP_TOKEN: "iafsHcMfvAEWtcTO6FTtc40jBuAl63VF"
```

如果 Token 来源不明确或已有段时间，可能已过期。

---

## 临时解决方案

在等待问题解决期间，可以：

1. **禁用 MCP 工具**（在 main.py 中注释掉工具注册）
2. **使用Mock 数据**（创建本地模拟工具替代 MCP）
3. **仅使用 Python 代码执行**（有限但可用）

```python
# Example: Mock tool for testing
def mock_query_nearby_stores(latitude: float, longitude: float) -> str:
    """Mock implementation"""
    return json.dumps({
        "stores": [
            {"id": "S001", "name": "Store 1", "distance": 1.2},
            {"id": "S002", "name": "Store 2", "distance": 2.5},
        ]
    })
```

---

## 推荐的后续步骤

1. **优先级 HIGH**: 向 MCP Server 管理员获取正确的工具列表
2. **优先级 HIGH**: 确认 Token 的有效期和权限
3. **优先级 MEDIUM**: 获取 MCP Server 的 API 文档
4. **优先级 MEDIUM**: 检查是否有新的 Token 或认证方式

---

## 参考文件

已生成的诊断数据：
- `debug_mcp_api.py` - 基础 API 诊断
- `debug_mcp_api_advanced.py` - 高级 API 诊断
- `debug_mcp_response.py` - 详细响应分析
- `find_tool_names.py` - 工具名称探索
- 诊断输出日志文件

---

## 如果上述都解决不了...

尝试MCP 官方标准协议而不是 HTTP:
- 参考: https://modelcontextprotocol.io/
- 可能需要使用 `stdio` 或 `sse` 传输
- 需要与 MCP Server 维护者确认
