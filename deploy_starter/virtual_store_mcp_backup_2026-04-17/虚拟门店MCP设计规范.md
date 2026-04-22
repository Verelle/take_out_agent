# 虚拟门店 MCP 设计规范

## 核心原则：接口对齐，数据自由

工具签名（参数+返回结构）应尽量与真实MCP保持一致。

**原因：**
- 演示时可无缝切换"虚拟门店"和"真实麦当劳"，只换MCP Server，Agent代码不动
- 技术组员在Cherry Studio里调试真实MCP时，虚拟MCP可作为对照基准
- 评委看到"这套架构可以接任何门店的MCP"，技术可扩展性加分

---

## 数据结构设计注意事项

### 1. 工具命名与参数名保持一致

如果麦当劳MCP有 `search_nearby_stores(latitude, longitude, radius_km)`，虚拟MCP就用同样的参数名，不要改成 `lat/lng` 或 `distance`。

### 2. 返回结构要稳定且可预期

Agent依赖返回结构做决策，字段名乱了会导致Agent解析失败。统一返回格式：

```python
{
  "success": bool,
  "data": {...},       # 实际数据
  "error": str | None  # 错误信息
}
```

### 3. 虚拟数据要"够真"

- 门店坐标用真实上海坐标（不要用 0,0）
- 菜单价格、营业时间符合常识
- 库存状态要有变化（不能全是"有货"，演示时才有意思）

### 4. 枚举值与真实MCP对齐

订单状态等枚举值保持一致，例如：

```
pending → confirmed → preparing → ready → completed
```

不要自己发明状态名。

### 5. 字段层级结构完全一致

假设麦当劳真实MCP的 `get_menu` 返回：

```json
{
  "store_id": "xxx",
  "categories": [
    {
      "name": "汉堡",
      "items": [{"id": "...", "name": "巨无霸", "price": 24.9, "available": true}]
    }
  ]
}
```

虚拟MCP照此结构返回，门店名字换成虚拟门店，数据自己编，但**字段名和层级结构完全一致**。

---

## 代码结构设计注意事项

### 推荐目录结构

```
virtual_store_mcp/
├── server.py          # MCP Server 入口，注册所有工具
├── data/
│   ├── stores.json    # 门店数据
│   ├── menu.json      # 菜单数据
│   └── orders.json    # 运行时订单状态（内存或文件）
├── tools/
│   ├── store.py       # 门店相关工具（搜索、详情）
│   ├── menu.py        # 菜单相关工具（查询、分类）
│   └── order.py       # 订单相关工具（创建、查询、取消）
└── README.md
```

### 关键设计点

1. **工具函数与数据分离**
   `tools/` 只做逻辑，数据全在 `data/`，方便演示时临时改数据。

2. **订单状态用内存dict就够**
   演示场景不需要持久化，`orders = {}` 全局变量简单可靠。

3. **每个工具加docstring**
   MCP框架会把docstring当作工具描述传给LLM，写清楚参数含义。

4. **错误处理要明确**
   门店不存在、菜品售罄等情况返回清晰的error message，不要抛异常。
