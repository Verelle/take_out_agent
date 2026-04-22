# BridgeX E2E 修复 + 验证手册
> **给 Copilot**：按第2节的4个任务顺序修改代码，修完后按第3节验证。
> **给 Vera**：第1节是逻辑链图，看不下去直接跳第4节排查表。

---

## 第1节：逻辑链全图（理解用）

### 1.1 一次完整点餐的数据流

```
用户说："我在上海徐家汇，想吃个双层牛肉堡，哪家便宜？"
         │
         ▼
    [Agent: Friday]
         │
    ┌────┴─────────────────────────────────────┐
    │  Step 1: 找附近门店（两家同时查）           │
    │  query_nearby_stores(city="上海",          │
    │      keyword="徐家汇")                    │
    │  vstore_query_nearby_stores(city="上海",   │
    │      keyword="徐家汇")                    │
    └────┬─────────────────────────────────────┘
         │
    拿到：麦当劳门店 storeCode (如 "0801")
          星选汉堡门店 storeCode = "SX001"
         │
    ┌────┴─────────────────────────────────────┐
    │  Step 2: 查菜单（找到对应品类）             │
    │  query_meals("0801", orderType=1)          │
    │  vstore_query_meals("SX001", orderType=1) │
    └────┬─────────────────────────────────────┘
         │
    拿到：麦当劳 productCode (如 "BG0001")
          星选汉堡 mealCode = "SX_BG001"（22.9元）
         │
    ┌────┴─────────────────────────────────────┐
    │  Step 3: 麦当劳查优惠券                    │
    │  available_coupons()                      │
    │  query_my_coupons()                       │
    └────┬─────────────────────────────────────┘
         │
    拿到：麦当劳可用券（如"双层牛堡8折券"）
         │
    ┌────┴─────────────────────────────────────┐
    │  Step 4: 两家分别算价格                    │
    │  calculate_price("0801", items=[{          │
    │      productCode:"BG0001", quantity:1,    │
    │      couponId:"xxx", couponCode:"yyy"}])  │
    │                                           │
    │  vstore_calculate_price("SX001", items=[{ │
    │      productCode:"SX_BG001", quantity:1}])│
    └────┬─────────────────────────────────────┘
         │
    拿到：麦当劳用券后价格（如 21.5元）
                              ↑
    关键：vstore_calculate_price 返回的
    data.price 应是 22.9（元），
    同时 data.takeWayList 里有取餐方式代码
                              │
    ┌────┴─────────────────────────────────────┐
    │  Step 5: Agent 对比 + 推荐                 │
    │  如：麦当劳用券 21.5元 < 星选汉堡 22.9元    │
    │  → 推荐麦当劳                             │
    └────┬─────────────────────────────────────┘
         │
    用户确认后：
    ┌────┴─────────────────────────────────────┐
    │  Step 6: 下单                             │
    │  vstore_create_order("SX001",             │
    │      takeWayCode="locker-in",  ← 从Step4拿│
    │      items=[{productCode:"SX_BG001",...}])│
    └────┬─────────────────────────────────────┘
         │
    拿到：orderId, totalAmount（应与Step4一致）
         │
    ┌────┴─────────────────────────────────────┐
    │  Step 7: 查订单（确认状态）                 │
    │  vstore_query_order(orderId="SX20260417xx")│
    └─────────────────────────────────────────┘
```

### 1.2 当前已知的断点位置

```
Step 4 ──→ vstore_calculate_price
               └─ pricing_corrected.py
                      ├─ ❌ Bug1: 价格×100（返回2290而非22.9）
                      └─ ❌ Bug1: takeWayList=[]（Step6拿不到取餐码）

Step 6 ──→ vstore_create_order
               ├─ ❌ Bug2: mcp_client.py没有takeWayCode参数
               └─ orders_corrected.py
                      ├─ ❌ Bug2: takeWayCode缺失直接返回400
                      ├─ ❌ Bug3: unit_price硬编码=20元（与Step4不一致）
                      └─ ❌ Bug3: storeName="虚拟快餐店"（旧品牌名）
```

---

## 第2节：Copilot 修改任务单

> **执行顺序**：Task 1 → Task 2 → Task 3 → Task 4（有依赖关系，不要乱序）

---

### Task 1：修改 `temp_mcp_framework/tools/pricing_corrected.py`

**修改点 A**：在 `find_meal_price` 函数下方（约第35行后）新增 `find_meal_name` 函数

```python
def find_meal_name(meal_code: str, store_code: str = None) -> str:
    """根据餐品编码查找餐品名称"""
    menu_data = load_menu_data()
    for store_menu in menu_data:
        if store_code and store_code != store_menu.get("storeCode"):
            continue
        for category in store_menu.get("categories", []):
            for item in category.get("items", []):
                if item.get("mealCode") == meal_code:
                    return item.get("mealName", meal_code)
    return meal_code
```

**修改点 B**：在 `calculate_price` 函数内，找到价格计算部分，改为以下内容（去掉所有 `×100` 和 `÷100`）

```python
        # 计算价格（单位：元）
        product_original_price = 0.0
        product_price = 0.0
        discount = 0.0
        product_list = []

        for item in items:
            product_code = item["productCode"]
            quantity = item["quantity"]
            coupon_id = item.get("couponId")
            coupon_code = item.get("couponCode")

            unit_price = find_meal_price(product_code, storeCode)  # 返回元（float）
            original_subtotal = unit_price * quantity

            # 优惠逻辑：有券打8折
            subtotal = original_subtotal
            if coupon_id and coupon_code:
                discount_amount = original_subtotal * 0.2
                subtotal = original_subtotal - discount_amount
                discount += discount_amount

            product_original_price += original_subtotal
            product_price += subtotal

            product_list.append({
                "productCode": product_code,
                "productName": find_meal_name(product_code, storeCode),
                "quantity": quantity,
                "originalSubtotal": round(original_subtotal, 2),
                "subtotal": round(subtotal, 2)
            })

        # 配送费（元）
        delivery_original_price = 6.0 if orderType == 2 else 0.0
        delivery_price = delivery_original_price

        original_price = product_original_price + delivery_original_price
        price = product_price + delivery_price
```

**修改点 C**：`data` 字段里所有数字字段换成 `round(..., 2)`，同时 `takeWayList` 加默认值

```python
            "data": {
                "productOriginalPrice": round(product_original_price, 2),
                "productPrice": round(product_price, 2),
                "deliveryOriginalPrice": round(delivery_original_price, 2),
                "deliveryPrice": round(delivery_price, 2),
                "originalPrice": round(original_price, 2),
                "discount": round(discount, 2),
                "price": round(price, 2),
                "productList": product_list,
                "takeWayList": [{"code": "locker-in", "name": "自取"}],
                "mealAssistanceList": []
            }
```

**修改点 D**：文件末尾 `if __name__ == "__main__"` 的测试代码，把所有 `data['xxx']/100` 改为直接 `data['xxx']`

---

### Task 2：修改 `temp_mcp_framework/tools/orders_corrected.py`

**修改点 A**：文件顶部 import 区域后，添加路径和辅助函数

```python
import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
STORES_FILE = os.path.join(DATA_DIR, "stores.json")

# 将 tools 目录加入路径，以便 import pricing_corrected
sys.path.insert(0, os.path.join(BASE_DIR, "tools"))
from pricing_corrected import find_meal_price, find_meal_name

def find_store_name(store_code: str) -> str:
    """根据门店编码从 stores.json 查找门店名称"""
    try:
        with open(STORES_FILE, 'r', encoding='utf-8') as f:
            stores = json.load(f)
        for store in stores:
            if store.get("storeCode") == store_code:
                return store.get("storeName", f"星选汉堡({store_code})")
    except Exception:
        pass
    return f"星选汉堡({store_code})"
```

**修改点 B**：`create_order` 函数内，找到 takeWayCode 的强制验证，改为软兜底

```python
        # 旧代码（删除）：
        # if orderType == 1 and not takeWayCode:
        #     return {"success": False, "code": 400, "message": "到店场景下takeWayCode参数必填", ...}

        # 新代码（替换）：
        if orderType == 1 and not takeWayCode:
            takeWayCode = "locker-in"  # 默认自取，避免 Agent 因拿不到 takeWayCode 而下单失败
```

**修改点 C**：`create_order` 函数内，找到商品价格计算部分，替换硬编码

```python
        # 旧代码（删除）：
        # unit_price = 2000  # 硬编码：20元（分）
        # price = unit_price * quantity
        # "price": f"{price/100:.2f}",

        # 新代码（替换）：
        unit_price = find_meal_price(product_code, storeCode)  # 从菜单读取（元）
        price = unit_price * quantity

        order_product_list.append({
            "productName": find_meal_name(product_code, storeCode),
            "quantity": quantity,
            "price": f"{price:.2f}",
            "comboItemList": [
                {"itemName": find_meal_name(product_code, storeCode), "itemQuantity": quantity}
            ]
        })
        total_amount += price
```

**修改点 D**：找到 `storeName` 字段，更换为读取函数

```python
        # 旧：
        # "storeName": f"虚拟快餐店({storeCode if storeCode else '默认门店'})",

        # 新：
        "storeName": find_store_name(storeCode) if storeCode else "星选汉堡",
```

**修改点 E**：找到 `totalAmount` 和 `realTotalAmount` 字段，去掉 `/100`

```python
        # 旧：
        # "totalAmount": f"{total_amount/100:.2f}",
        # "realTotalAmount": f"{total_amount/100:.2f}",

        # 新：
        "totalAmount": f"{total_amount:.2f}",
        "realTotalAmount": f"{total_amount:.2f}",
```

---

### Task 3：修改 `deploy_starter/mcp_client.py`

**只改一处**：找到 `vstore_create_order` 函数，添加 `takeWayCode` 参数

```python
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
```

---

### Task 4：修改 `temp_mcp_framework/tools/coupons_corrected.py`（低优先级）

**清空虚拟优惠券数据**（避免测试虚拟MCP时看到麦当劳品牌数据）：

```python
# 旧（删除3条数据）：
VIRTUAL_COUPONS = [...]
USER_COUPONS = [...]

# 新：
VIRTUAL_COUPONS = []   # 星选汉堡暂无优惠券活动
USER_COUPONS = []      # 星选汉堡暂无优惠券活动
```

---

## 第3节：验证步骤（PowerShell 脚本方式）

> **前提**：所有 Task 改完后，先重启虚拟MCP Server（新开一个 PowerShell 窗口）：
> ```powershell
> cd C:\Users\Vera\.openclaw\workspace\temp_mcp_framework
> python server_corrected.py
> ```
> 确认终端输出 `启动星选汉堡 MCP Server...` 后，在另一个窗口执行以下验证命令。

> **说明**：所有命令均为 PowerShell 格式，使用 `$body = @{...} | ConvertTo-Json -Depth 10` 构造请求体，避免 JSON 转义问题。

---

### Step V1：握手验证（serverInfo 应含"星选汉堡"）

```powershell
$body = @{
    jsonrpc = "2.0"
    id      = 1
    method  = "initialize"
    params  = @{
        protocolVersion = "2024-11-05"
        capabilities    = @{}
        clientInfo      = @{ name = "test"; version = "1.0" }
    }
} | ConvertTo-Json -Depth 10

curl -s -X POST http://127.0.0.1:8000 `
  -H "Content-Type: application/json" `
  -d $body
```

✅ 预期：返回 JSON 中 `result.serverInfo.name` = `"star-select-burger-mcp-server"`

---

### Step V2：价格单位验证（核心 Bug 1 — 应返回 22.9，不是 2290）

```powershell
$body = @{
    jsonrpc = "2.0"
    id      = 2
    method  = "tools/call"
    params  = @{
        name      = "calculate-price"
        arguments = @{
            storeCode = "SX001"
            orderType = 1
            items     = @(
                @{ productCode = "SX_BG001"; quantity = 1 }
            )
        }
    }
} | ConvertTo-Json -Depth 10

curl -s -X POST http://127.0.0.1:8000 `
  -H "Content-Type: application/json" `
  -d $body
```

✅ 预期：
- `result.data.price` = `22.9`（**不是 2290**）
- `result.data.productList[0].productName` = `"星选招牌双层牛堡"`（不是 "虚拟商品-SX_BG001"）
- `result.data.takeWayList` = `[{"code":"locker-in","name":"自取"}]`（不是空数组）

❌ 如果还是 2290：Task 1 修改点 B/C 没生效，检查虚拟MCP是否重启

---

### Step V3：下单验证（核心 Bug 2 — 不再报 400，storeName 含"星选汉堡"）

```powershell
$body = @{
    jsonrpc = "2.0"
    id      = 3
    method  = "tools/call"
    params  = @{
        name      = "create-order"
        arguments = @{
            storeCode   = "SX001"
            orderType   = 1
            takeWayCode = "locker-in"
            items       = @(
                @{ productCode = "SX_BG001"; quantity = 1 }
            )
        }
    }
} | ConvertTo-Json -Depth 10

curl -s -X POST http://127.0.0.1:8000 `
  -H "Content-Type: application/json" `
  -d $body
```

✅ 预期：
- `result.success` = `true`（不是 false/400）
- `result.data.orderDetail.storeName` 包含 `"星选汉堡"`（不是 "虚拟快餐店"）
- `result.data.orderDetail.totalAmount` = `"22.90"`（与 V2 的 price 一致）

❌ 如果 `success=false, message="到店场景下takeWayCode参数必填"`：Task 2 修改点 B 没生效
❌ 如果 `totalAmount="20.00"`：Task 2 修改点 C 没生效
❌ 如果 `storeName="虚拟快餐店"`：Task 2 修改点 D 没生效

---

### Step V4：价格一致性验证（V2 的 price == V3 的 totalAmount）

不需要额外命令，对比 V2 和 V3 的输出：

```
V2 result.data.price                    →  22.9
V3 result.data.orderDetail.totalAmount  →  "22.90"
```

✅ 两者数值相同（允许 `22.9` vs `"22.90"` 的格式差异）= 价格一致性通过

---

### Step V5：查订单验证（用 V3 返回的 orderId）

先从 V3 的输出中找到 `result.data.orderId` 的值（格式如 `VS20260417XXXXXXXX`），替换下方的 `YOUR_ORDER_ID`：

```powershell
$orderId = "YOUR_ORDER_ID"   # ← 替换为 V3 返回的实际 orderId

$body = @{
    jsonrpc = "2.0"
    id      = 5
    method  = "tools/call"
    params  = @{
        name      = "query-order"
        arguments = @{
            orderId = $orderId
        }
    }
} | ConvertTo-Json -Depth 10

curl -s -X POST http://127.0.0.1:8000 `
  -H "Content-Type: application/json" `
  -d $body
```

✅ 预期：`result.data.orderStatus` = `"待支付"`，`result.data.storeName` 含 "星选汉堡"

---

### Step V6：验证 Agent 端工具签名（mcp_client.py 改动是否生效）

在 `deploy_starter/` 目录的 PowerShell 中执行：

```powershell
cd C:\Users\Vera\.openclaw\workspace\modelstudio-agent-starter\deploy_starter
python -c "import inspect; from mcp_client import vstore_create_order; print(list(inspect.signature(vstore_create_order).parameters.keys()))"
```

✅ 预期输出：`['storeCode', 'beCode', 'orderType', 'takeWayCode', 'items']`
❌ 如果没有 `takeWayCode`：Task 3 修改没生效

---

## 第4节：快速排查表

| 症状 | 最可能原因 | 定位文件 | 关键行 |
|------|-----------|---------|--------|
| `data.price = 2290` | ×100 未删除 | `pricing_corrected.py` | `original_subtotal = unit_price * quantity * 100` |
| `data.takeWayList = []` | takeWayList 未加默认值 | `pricing_corrected.py` | `"takeWayList": []` |
| 下单返回 `400 takeWayCode必填` | 强制校验未改为软兜底 | `orders_corrected.py` | `if orderType == 1 and not takeWayCode: return 400` |
| `totalAmount = "20.00"` | unit_price 仍是硬编码 | `orders_corrected.py` | `unit_price = 2000` |
| `storeName = "虚拟快餐店"` | storeName 字段未更新 | `orders_corrected.py` | `f"虚拟快餐店({storeCode})"` |
| `productName = "虚拟商品-SX_BG001"` | find_meal_name 未添加 | `pricing_corrected.py` | `"productName": f"虚拟商品-{product_code}"` |
| vstore_create_order 没有 takeWayCode 参数 | mcp_client.py 未更新 | `mcp_client.py` | `def vstore_create_order(storeCode, beCode, orderType, items)` |
| 修改后虚拟MCP返回旧数据 | Server 没有重启 | 终端 | 按 Ctrl+C 重启 `python server_corrected.py` |
| `ImportError: pricing_corrected` | 路径未加入 sys.path | `orders_corrected.py` | `sys.path.insert(0, ...)` 这行 |
| 验证步骤 V6 缺少 takeWayCode | Task 3 改动未保存 | `mcp_client.py` | `def vstore_create_order(...)` 参数列表 |

---

## 附：验证文件清单

修改完成后，在任意目录创建以下5个 json 文件，按顺序跑 curl 命令：

```
v1_init.json    ← Step V1（握手）
v2_calc.json    ← Step V2（算价格，验证核心Bug）
v3_order.json   ← Step V3（下单，验证核心Bug）
v5_query.json   ← Step V5（查订单，需先用V3的orderId替换）
```

全部通过 = **e2e 核心链路修复完成**。

---

*文档版本：2026-04-17 v2 | 针对 BridgeX pricing/orders/mcp_client 三文件 Bug 修复*
