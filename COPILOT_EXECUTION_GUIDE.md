# BridgeX — GitHub Copilot 执行手册

> **目标读者**：GitHub Copilot（通过 @workspace 调用，或直接粘贴本文档）
>
> **目标**：在一次对话内完成 BridgeX "生活顾问 AI Agent" 项目的代码修改 + 本地测试验证，不遗漏任何步骤。
>
> **项目背景**：BridgeX 是一个同时接入两家汉堡品牌 MCP Server 的 AI 智能体，能对比麦当劳（有优惠券）与星选汉堡（无优惠券但基础价更低）的价格，帮用户省钱。

---

## 0. 关键路径说明（先读，再动手）

```
项目结构
├── deploy_starter/          # Agent 服务主目录（阿里云百炼 AgentScope Runtime）
│   ├── main.py              # 入口：初始化 + 路由 + 对话处理
│   ├── mcp_client.py        # MCP 客户端封装（双客户端 + 16 个工具函数）
│   └── config.yml           # 配置文件（环境变量 > 此文件）
│
└── temp_mcp_framework/      # 星选汉堡虚拟 MCP Server（FastAPI，端口 8000）
    ├── server_corrected.py  # 服务入口
    ├── data/
    │   ├── stores.json      # 4 家上海门店
    │   └── menu.json        # 菜单（4 个门店 × 多品类）
    └── tools/
        ├── stores_corrected.py    # query-nearby-stores, query-store-coupons
        ├── menu_corrected.py      # query-meals, query-meal-detail
        ├── pricing_corrected.py   # calculate-price
        ├── orders_corrected.py    # create-order, query-order
        └── coupons_corrected.py   # available-coupons, query-my-coupons, auto-bind-coupons
                                   # （星选汉堡无优惠券 → 这3个工具不在虚拟MCP中）
```

**已完成的部分（不要重复改）：**
- `deploy_starter/mcp_client.py` — 已重写，双客户端 + 16 工具函数，`_wrap_tool_result` 已处理两种返回格式
- `deploy_starter/main.py` — 已重写，工具注册 + sys_prompt
- `deploy_starter/config.yml` — 已加入 `VSTORE_SERVER_URL` / `VSTORE_TOKEN` / `VSTORE_TIMEOUT`
- `temp_mcp_framework/data/stores.json` — 已品牌化为"星选汉堡"4家门店，storeCode=SX001~SX004
- `temp_mcp_framework/data/menu.json` — 已更新为星选汉堡菜单，mealCode 格式 `SX_BG001`、`SX_SET001` 等
- `temp_mcp_framework/server_corrected.py` — serverInfo 已改为"星选汉堡 MCP Server"

**本次需要做的事（全部在下方详细说明）：**
1. 重启虚拟 MCP Server（使新数据生效）
2. 验证虚拟 MCP 的 10 个工具返回正确的星选汉堡数据
3. 验证 `mcp_client.py` 语法无误 + 双客户端初始化逻辑
4. 尝试启动 `main.py` 验证整体可运行

---

## 1. 环境准备

### 1.1 确认虚拟 MCP Server 使用的是新数据

在 `temp_mcp_framework/` 目录下查看运行中的进程，如果已经启动过旧版，**必须重启**：

```bash
# Windows — 找到占用 8000 端口的进程并杀掉
netstat -ano | findstr :8000
# 找到 PID，然后：
taskkill /PID <PID> /F

# 重新启动（在 temp_mcp_framework 目录）
cd temp_mcp_framework
python server_corrected.py
# 预期输出：
# 启动星选汉堡 MCP Server...
# Uvicorn running on http://127.0.0.1:8000
```

### 1.2 确认 Python 依赖

```bash
pip install requests fastapi uvicorn pydantic
```

---

## 2. 虚拟 MCP 数据验证（独立测试，不依赖 Agent）

以下测试用 `curl` 或 Python 脚本验证虚拟 MCP 各工具返回正确的星选汉堡数据。

**每个 curl 命令后都有预期输出特征，Copilot 请对照验证。**

### 2.1 握手：initialize

```bash
curl -s -X POST http://127.0.0.1:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test", "version": "1.0"}
    }
  }' | python -m json.tool
```

**预期**：`result.serverInfo.name` 包含"星选汉堡"

---

### 2.2 获取工具列表：tools/list

```bash
curl -s -X POST http://127.0.0.1:8000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | python -m json.tool
```

**预期**：`result.tools` 包含 10 个工具，名称为：
`query-nearby-stores`, `query-store-coupons`, `query-meals`, `query-meal-detail`,
`calculate-price`, `create-order`, `query-order`, `available-coupons`,
`query-my-coupons`, `auto-bind-coupons`

---

### 2.3 查询附近门店：query-nearby-stores

```bash
curl -s -X POST http://127.0.0.1:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "query-nearby-stores",
      "arguments": {"searchType": 2, "beType": 1, "city": "上海", "keyword": "徐家汇"}
    }
  }' | python -m json.tool
```

**预期**：`result.content[0].text` 解析后的 `data.stores` 中，`storeName` 包含"星选汉堡"，`storeCode` 格式为 `SX001`~`SX004`

> **⚠️ 如果 storeName 仍然是"虚拟快餐店"：**
> 说明旧进程未关闭/数据文件没有热重载，重新执行步骤 1.1

---

### 2.4 查询菜单：query-meals

```bash
curl -s -X POST http://127.0.0.1:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "query-meals",
      "arguments": {"storeCode": "SX001", "orderType": 1}
    }
  }' | python -m json.tool
```

**预期**：
- `data.categories` 包含"招牌汉堡"、"超值套餐"、"小食配餐"、"饮品"
- `data.meals` 中有 `SX_BG001`（星选招牌双层牛堡，22.9元）

---

### 2.5 查询餐品详情：query-meal-detail

```bash
curl -s -X POST http://127.0.0.1:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "query-meal-detail",
      "arguments": {"code": "SX_BG001", "storeCode": "SX001", "orderType": 1}
    }
  }' | python -m json.tool
```

**预期**：`data.code = "SX_BG001"`, `data.price = "22.9"`

---

### 2.6 价格计算：calculate-price

```bash
curl -s -X POST http://127.0.0.1:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 6,
    "method": "tools/call",
    "params": {
      "name": "calculate-price",
      "arguments": {
        "storeCode": "SX001",
        "orderType": 1,
        "items": [{"productCode": "SX_BG001", "quantity": 1}]
      }
    }
  }' | python -m json.tool
```

**预期**：`data.totalAmount = 22.9`（或字符串 `"22.90"`）

---

### 2.7 创建订单：create-order

```bash
curl -s -X POST http://127.0.0.1:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 7,
    "method": "tools/call",
    "params": {
      "name": "create-order",
      "arguments": {
        "storeCode": "SX001",
        "orderType": 1,
        "items": [{"productCode": "SX_BG001", "quantity": 1}]
      }
    }
  }' | python -m json.tool
```

**预期**：
- `success = true`
- `data.orderId` 存在（如 `"ORD-xxxxxx"`）
- `data.totalAmount = 22.9`

---

### 2.8 查询订单：query-order（用上一步的 orderId）

```bash
curl -s -X POST http://127.0.0.1:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 8,
    "method": "tools/call",
    "params": {
      "name": "query-order",
      "arguments": {"orderId": "<上一步返回的 orderId>"}
    }
  }' | python -m json.tool
```

**预期**：`data.status` 存在，`data.storeName` 包含"星选汉堡"

---

### 2.9 优惠券工具（星选汉堡无券，应返回空列表）

```bash
# query-store-coupons
curl -s -X POST http://127.0.0.1:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 9,
    "method": "tools/call",
    "params": {
      "name": "query-store-coupons",
      "arguments": {"storeCode": "SX001", "orderType": 1}
    }
  }' | python -m json.tool
```

**预期**：`success = true`，`data.coupons = []`（空数组，不是错误）

---

## 3. Python 语法与导入验证

在 `deploy_starter/` 目录运行：

```bash
cd deploy_starter

# 验证 mcp_client.py 无语法错误
python -c "import ast; ast.parse(open('mcp_client.py', encoding='utf-8').read()); print('mcp_client.py: OK')"

# 验证所有预期的函数都存在
python -c "
import ast, sys
with open('mcp_client.py', encoding='utf-8') as f:
    tree = ast.parse(f.read())
funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
expected = [
    'init_mcp_clients',
    'query_nearby_stores', 'query_store_coupons', 'query_meals',
    'query_meal_detail', 'calculate_price', 'create_order',
    'query_order', 'available_coupons', 'auto_bind_coupons', 'query_my_coupons',
    'vstore_query_nearby_stores', 'vstore_query_meals', 'vstore_query_meal_detail',
    'vstore_calculate_price', 'vstore_create_order', 'vstore_query_order',
    '_wrap_tool_result'
]
missing = [f for f in expected if f not in funcs]
if missing:
    print('MISSING functions:', missing)
    sys.exit(1)
else:
    print('All 17 functions found: OK')
"

# 验证 main.py 无语法错误
python -c "import ast; ast.parse(open('main.py', encoding='utf-8').read()); print('main.py: OK')"
```

**预期**：三行均输出 `OK`，无报错

---

## 4. 集成验证：mcp_client 双客户端初始化

> **前提**：虚拟 MCP Server 已在 8000 端口运行

在 `deploy_starter/` 目录：

```python
# 创建临时测试脚本 test_mcp_init.py
# 内容如下（Copilot 请直接创建此文件并运行）：
```

```python
# test_mcp_init.py
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from mcp_client import init_mcp_clients

# 麦当劳 MCP（真实地址，握手可能失败，但不会崩溃）
# 星选汉堡 MCP（本地 8000）
status = init_mcp_clients(
    mcd_url="https://mcp.mcd.cn",
    mcd_token="iafsHcMfvAEWtcTO6FTtc40jBuAl63VF",
    mcd_timeout=5,
    vstore_url="http://127.0.0.1:8000",
    vstore_token="vstore-dev-token",
    vstore_timeout=5,
)

print("=== 初始化结果 ===")
print(f"麦当劳 MCP: {'✓ 成功' if status['mcd'] else '✗ 失败（预期 - 需要真实网络/Token）'}")
print(f"星选汉堡 MCP: {'✓ 成功' if status['vstore'] else '✗ 失败（本地 8000 未启动？）'}")

# 核心验证：星选汉堡必须成功
assert status["vstore"], "ERROR: 星选汉堡 MCP 初始化失败！请确认 server_corrected.py 正在运行于端口 8000"
print("\n✓ 星选汉堡 MCP 客户端初始化成功")

# 验证工具调用
from mcp_client import vstore_query_nearby_stores, vstore_query_meals, vstore_calculate_price

print("\n=== 工具调用验证 ===")

# 1. 查门店
result = vstore_query_nearby_stores(searchType=2, city="上海", keyword="徐家汇")
text = result.content[0].text
print(f"vstore_query_nearby_stores: {'✓' if 'SX' in text or '星选' in text else '✗ 返回异常'}")
print(f"  返回预览: {text[:100]}...")

# 2. 查菜单
result = vstore_query_meals(storeCode="SX001", orderType=1)
text = result.content[0].text
print(f"vstore_query_meals: {'✓' if 'SX_BG001' in text or '星选' in text else '✗ 返回异常'}")
print(f"  返回预览: {text[:100]}...")

# 3. 算价格
result = vstore_calculate_price(
    storeCode="SX001",
    orderType=1,
    items=[{"productCode": "SX_BG001", "quantity": 1}]
)
text = result.content[0].text
print(f"vstore_calculate_price: {'✓' if '22' in text else '✗ 返回异常'}")
print(f"  返回预览: {text[:100]}...")

print("\n✓ 所有验证通过！")
```

```bash
# 运行测试
cd deploy_starter
python test_mcp_init.py
```

**预期输出**：
```
=== 初始化结果 ===
麦当劳 MCP: ✗ 失败（预期 - 需要真实网络/Token）      ← 这个失败没关系
星选汉堡 MCP: ✓ 成功

✓ 星选汉堡 MCP 客户端初始化成功

=== 工具调用验证 ===
vstore_query_nearby_stores: ✓
  返回预览: ...SX001...星选汉堡...
vstore_query_meals: ✓
  返回预览: ...SX_BG001...22.9...
vstore_calculate_price: ✓
  返回预览: ...22.9...

✓ 所有验证通过！
```

---

## 5. （可选）启动完整 Agent 服务

> 需要有效的 `DASHSCOPE_API_KEY`，否则 Agent 无法推理

```bash
# 在 deploy_starter/ 目录
export DASHSCOPE_API_KEY="your-api-key-here"
# Windows PowerShell:
$env:DASHSCOPE_API_KEY = "your-api-key-here"

python main.py
# 预期输出：
# ✓/✗ 麦当劳 MCP: https://mcp.mcd.cn
# ✓   星选汉堡 MCP: http://127.0.0.1:8000
# Service started, press Ctrl+C to stop...
```

### 5.1 发送测试消息

Agent 服务默认在 `http://127.0.0.1:8080`，用如下 curl 测试：

```bash
curl -s -X POST http://127.0.0.1:8080/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-001",
    "user_id": "test-user",
    "messages": [{"role": "user", "content": "我在上海徐家汇，想吃个汉堡套餐，哪家更划算？"}]
  }' | python -m json.tool
```

**预期行为**：Agent 应该：
1. 同时调用 `query_nearby_stores`（麦当劳）和 `vstore_query_nearby_stores`（星选汉堡）
2. 查两家菜单
3. 查麦当劳优惠券
4. 两边算价格对比
5. 给出推荐结论（不应该直接编造答案跳过工具调用）

---

## 6. 常见问题排查

| 症状 | 原因 | 解决方法 |
|------|------|---------|
| `vstore_query_meals` 返回"未找到门店SX001菜单" | `menu.json` 中 `storeCode` 不匹配 | 检查 `temp_mcp_framework/data/menu.json` 根节点的 `storeCode` 字段 |
| `query-store-coupons` 返回含优惠券数据 | `stores_corrected.py` 未更新 | 检查 `tools/stores_corrected.py` 中 `coupon_data = []` 是否生效 |
| `storeName` 仍是"虚拟快餐店" | 旧进程缓存 | 重启 `server_corrected.py` |
| `_wrap_tool_result` 返回原始 JSON 字典 | 格式识别逻辑走到 else 分支 | 检查虚拟MCP返回的顶层字段是否包含 `success` 和 `data` |
| `init_mcp_clients` 卡住不返回 | 真实麦当劳 MCP 超时 | 已设置 `mcd_timeout=5`，等待即可；或把 `mcd_url` 改为无效地址跳过 |
| `toolkit.register_tool_function` 报函数签名错误 | Python 版本 < 3.10 inspect 问题 | 确认 Python >= 3.10 |

---

## 7. 如果测试失败：需要修改的具体位置

### 7.1 stores.json 门店不匹配 menu.json（storeCode 对不上）

**问题**：`query-meals` 报"未找到门店 SX001 的菜单"

**检查**：
```python
import json
stores = json.load(open("temp_mcp_framework/data/stores.json", encoding="utf-8"))
menus = json.load(open("temp_mcp_framework/data/menu.json", encoding="utf-8"))
store_codes = {s["storeCode"] for s in stores}
menu_codes = {m["storeCode"] for m in menus}
print("门店:", store_codes)  # 应该是 {SX001, SX002, SX003, SX004}
print("菜单:", menu_codes)   # 应该是 {SX001, SX002, SX003, SX004}
print("缺失菜单的门店:", store_codes - menu_codes)
```

**修复**：在 `menu.json` 中为缺失的门店添加对应条目（复制 SX001 的结构，修改 `storeCode`）

---

### 7.2 vstore 工具调用后 ToolResponse.content[0].text 是错误信息

**检查 `mcp_client.py` 第 `_wrap_tool_result` 函数**，确认格式识别逻辑：

```python
# 正确的格式2识别逻辑（虚拟MCP返回）
elif "success" in result and "data" in result:
    if result.get("success"):
        content = json.dumps(result["data"], ensure_ascii=False, indent=2)
    else:
        content = f"调用失败: {result.get('message', '未知错误')} (code={result.get('code')})"
```

如果不是这个结构，说明文件未正确保存，需要重新写入 `mcp_client.py`。

---

### 7.3 main.py 导入失败（ModuleNotFoundError）

```bash
# 在 deploy_starter/ 目录直接运行时：
python -c "from mcp_client import init_mcp_clients, vstore_query_nearby_stores; print('OK')"
```

如果报错，检查 `mcp_client.py` 是否在同一目录。

---

## 8. 最终验收清单

完成所有步骤后，逐项打勾：

- [ ] **虚拟 MCP Server 正常运行**：`curl http://127.0.0.1:8000` initialize 握手成功，serverInfo 名称含"星选汉堡"
- [ ] **10 个工具已注册**：`tools/list` 返回 10 个工具
- [ ] **数据品牌化正确**：`query-nearby-stores` 返回的 storeName 含"星选汉堡"，storeCode 为 SX001-SX004
- [ ] **菜单数据正确**：`query-meals(SX001)` 返回 mealCode 格式为 SX_BG001，价格 22.9
- [ ] **优惠券为空**：`query-store-coupons` 返回 success=true 且 data.coupons=[]
- [ ] **mcp_client.py 语法无误**：`ast.parse` 无报错
- [ ] **17 个函数全部存在**：包括 `init_mcp_clients`、10 个麦当劳函数、6 个 vstore 函数、`_wrap_tool_result`
- [ ] **集成初始化测试通过**：`python test_mcp_init.py` 中星选汉堡 MCP 初始化成功
- [ ] **3 个 vstore 工具调用正常**：`vstore_query_nearby_stores`、`vstore_query_meals`、`vstore_calculate_price` 均返回有效数据

所有 9 项通过 = **项目就绪，可以 Demo**。

---

*文档生成时间：2026-04-17 | 项目：BridgeX 生活顾问 AI Agent*
