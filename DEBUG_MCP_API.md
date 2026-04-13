## 🔍 MCP Server API 404 错误的诊断和解决方案

### 问题描述
测试工具报错：
```
404 Client Error: Not Found for url: https://mcp.mcd.cn/tools/list-nutrition-foods
```

这表明 API 端点 `/tools/{tool_name}` 可能不是 MCP Server 的正确路由。

---

### 🛠️ 第一步：运行诊断脚本

执行以下命令来诊断 MCP Server 的真实 API 结构：

```bash
python debug_mcp_api.py
```

或者指定自定义的服务器地址和 Token：

```bash
python debug_mcp_api.py "https://mcp.mcd.cn" "iafsHcMfvAEWtcTO6FTtc40jBuAl63VF"
```

### 📊 诊断脚本会做什么

该脚本会自动尝试：
1. ✅ 测试根路径 `/` 
2. ✅ 测试常见的 API 查询方法：
   - `/tools` - 列出所有工具
   - `/api/tools` - 带 api 前缀
   - `/v1/tools` - API 版本前缀
   - `/capabilities` - 能力查询
   - `/health` - 健康检查
3. ✅ 尝试工具调用的多种格式
4. ✅ 检查响应头获取 API 信息

### 🎯 根据诊断结果修复

#### 场景1：如果成功返回 200（根路径）

服务器正常运行。检查响应体中是否包含：
- 工具列表
- API 文档或说明
- 支持的端点

#### 场景2：如果找到正确的工具列表端点

假设诊断发现正确的端点是 `/api/v1/tools/{tool_name}` 而不是 `/tools/{tool_name}`，那么需要修改 `mcp_client.py`：

**修改前：**
```python
def call_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{self.base_url}/tools/{tool_name}"
    # ...
```

**修改后：**
```python
def call_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{self.base_url}/api/v1/tools/{tool_name}"  # 修改路径
    # ...
```

#### 场景3：如果所有直接调用都失败（都是 404）

可能的原因和解决方案：

1. **Token 认证问题**
   - 检查 Token 是否过期或无效
   - 尝试获取新的 Token
   - 检查 Authorization header 格式是否正确

2. **服务器 URL 错误**
   - 确认 `https://mcp.mcd.cn` 是否可访问
   - 检查是否需要 VPN 或特殊网络配置
   - 尝试访问 `https://mcp.mcd.cn/health` 或 `/` 来确认连接

3. **API 路由可能使用 RPC 或 GraphQL**
   - 如果诊断发现响应中有 `jsonrpc` 字段，则使用的是 JSON-RPC
   - 示例修改：
   ```python
   def call_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
       url = f"{self.base_url}/rpc"  # RPC 统一端点
       rpc_payload = {
           "jsonrpc": "2.0",
           "method": tool_name,
           "params": payload,
           "id": 1
       }
       response = requests.post(url, json=rpc_payload, headers=self.headers, timeout=self.timeout)
       # ...
   ```

4. **API 完全不同的格式**
   - 联系 MCP Server 的管理员获取 API 文档
   - 根据实际的 API 文档调整 `call_tool` 方法

---

### 🔧 常见的修改示例

#### 如果 API 上下文是 `/api/v1/`
```python
url = f"{self.base_url}/api/v1/tools/{tool_name}"
```

#### 如果 API 需要工具名称转换（比如从 `list-nutrition-foods` 转换为 `listNutritionFoods`）
```python
# 驼峰命名转换
from inflection import camelize
camel_tool_name = camelize(tool_name.replace("-", "_"), uppercase_first_letter=False)
url = f"{self.base_url}/tools/{camel_tool_name}"
```

#### 如果使用自定义协议（如 MCP 标准协议）
可能需要使用 `stdio` 或 `sse` 传输而不是 HTTP POST。此时需要参考 [MCP 官方文档](https://modelcontextprotocol.io/)。

---

### 📋 诊断检查清单

运行诊断后，检查以下内容：

- [ ] 根路径 `/` 是否返回 200？
- [ ] 是否找到任何返回 200 的端点？
- [ ] 响应中是否包含工具列表或 API 说明？
- [ ] Authorization header 的格式是否正确？
- [ ] Token 是否仍然有效？
- [ ] URL 中是否有特殊的前缀或版本号？

---

### 💡 快速修复建议

如果诊断运行顺利但还是 404，最可能的原因是：

1. **Token 过期** → 获取新的 Token
2. **API 路径不对** → 根据诊断结果修改 URL
3. **工具名称格式不对** → 可能需要转换命名方式

---

### 返回主测试

修复 API 路径后，返回运行测试：

```bash
# 再次运行完整测试
python test_mcp_tools.py

# 或测试单个工具
python test_mcp_tools.py now_time_info
```

---

### 📞 获取支持

如果诊断仍无法解决问题：

1. 收集诊断脚本的完整输出
2. 检查 MCP Server 的官方文档
3. 联系 MCP Server 的维护者或 API 文档团队
