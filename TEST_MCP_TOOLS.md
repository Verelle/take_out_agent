# MCP 工具测试指南

本文档说明如何使用 `test_mcp_tools.py` 脚本来单独测试 MCP 工具的调用（不通过智能体）。

## 使用方法

### 方式一：批量测试所有工具

运行完整的测试套件，对所有已包装的 MCP 工具进行测试：

```bash
python test_mcp_tools.py
```

**输出**：
- 实时显示每个测试的执行结果（✓ 成功 或 ✗ 失败）
- 最后显示测试摘要（成功数、失败数）
- 将详细结果保存到 `mcp_test_results.json`

### 方式二：单个工具测试

测试特定的工具并查看详细结果：

```bash
python test_mcp_tools.py <tool_name> [args...]
```

**示例**：

```bash
# 测试获取当前时间（无参数）
python test_mcp_tools.py now_time_info

# 测试查询附近门店（需要纬度和经度）
python test_mcp_tools.py query_nearby_stores 31.0299 121.4312

# 测试列出营养信息（指定食品名）
python test_mcp_tools.py list_nutrition_foods "Big Mac"

# 测试查询菜单
python test_mcp_tools.py query_meals S001

# 测试查询用户优惠券
python test_mcp_tools.py query_my_coupons user123
```

## 支持的工具列表

### 基础信息查询
- `now_time_info` - 获取当前时间信息

### 门店和菜单
- `query_nearby_stores` - 查询附近门店（需要坐标）
- `query_meals` - 查询门店菜单
- `query_meal_detail` - 查询餐品详情
- `list_nutrition_foods` - 查询営养信息

### 配送地址
- `delivery_query_addresses` - 查询用户已保存地址
- `delivery_create_address` - 创建新配送地址

### 优惠券
- `query_store_coupons` - 查询门店优惠券
- `available_coupons` - 查询可领取优惠券
- `query_my_coupons` - 查询用户已有优惠券
- `auto_bind_coupons` - 自动领取优惠券

### 订单和价格
- `calculate_price` - 计算订单价格
- `create_order` - 创建订单
- `query_order` - 查询订单详情

### 营销和活动
- `campaign_calendar` - 查询营销活动日历

### 账户和积分
- `query_my_account` - 查询账户积分信息
- `mall_points_products` - 查询积分商城商品
- `mall_product_detail` - 查询商品详情
- `mall_create_order` - 使用积分兑换商品

## 测试结果说明

### 成功情况
```
[1] 测试 now_time_info... ✓ 成功
```

表示工具成功被调用，返回了结果。

### 失败情况
```
[2] 测试 query_nearby_stores... ✗ 失败: 麦当劳 MCP 调用失败: Connection refused
```

常见失败原因：
- **Connection refused**: MCP Server 没有启动或地址不对
- **Authorization failed**: Token 认证失败
- **Invalid parameters**: 工具参数不正确

## 配置

### 修改 MCP Server 地址

在脚本中修改 `MCPToolTester` 初始化：

```python
tester = MCPToolTester(
    base_url="http://your-server:port",  # 修改服务器地址
    token="your-token"                     # 修改认证 token
)
```

## 测试结果文件

批量测试完成后会生成 `mcp_test_results.json`，包含：

- 每个测试的名称、状态、返回结果和错误信息
- 支持后续分析和记录

## 扩展

如需添加更多测试用例，修改 `test_all_tools()` 中的 `test_cases` 列表：

```python
test_cases = [
    ("测试名称", 函数, 参数1, 参数2, ...),
    # ... 更多测试用例
]
```

## 前置条件

1. ✅ 依赖已安装：`pip install -r requirements.txt`
2. ✅ MCP Server 已启动
3. ✅ 正确配置了 MCP Server 地址和认证 token
