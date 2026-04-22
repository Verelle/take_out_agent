"""
优惠券相关工具模块 - 修正版
根据麦当劳MCP真实文档对齐接口
实现 available-coupons, query-my-coupons, auto-bind-coupons 工具
"""

import datetime
import uuid
from typing import Dict, Any, List

# 虚拟优惠券数据
VIRTUAL_COUPONS = []   # 星选汉堡暂无优惠券活动

# 用户已领取优惠券
USER_COUPONS = []      # 星选汉堡暂无优惠券活动

def available_coupons() -> Dict[str, Any]:
    """
    麦麦省券列表查询 - 修正版
    参数与麦当劳MCP的available-coupons完全一致
    
    参数:
      无
    
    返回:
      符合麦当劳MCP统一返回格式的结果（Markdown格式）
    """
    try:
        # 构建Markdown格式响应（与麦当劳MCP文档示例一致）
        markdown_content = "### 麦麦省优惠券列表：\n"
        
        for coupon in VIRTUAL_COUPONS:
            markdown_content += f"- 优惠券标题：{coupon['title']} \\\n"
            markdown_content += f"  状态：{coupon['status']} \\\n"
            markdown_content += f"  优惠券图片：\\\n"
            markdown_content += f"  <img src=\"{coupon['imageUrl']}\" height=\"auto\" width=\"300\">\n\n"
        
        # 构建响应结构（注意：data字段是字符串，不是JSON）
        response = {
            "success": True,
            "code": 200,
            "message": "请求成功",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": markdown_content
        }
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "code": 500,
            "message": f"查询优惠券列表时发生错误: {str(e)}",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": None
        }

def query_my_coupons() -> Dict[str, Any]:
    """
    我的优惠券查询 - 修正版
    参数与麦当劳MCP的query-my-coupons完全一致
    
    参数:
      无
    
    返回:
      符合麦当劳MCP统一返回格式的结果（Markdown格式）
    """
    try:
        # 构建Markdown格式响应
        markdown_content = "### 我的优惠券列表：\n"
        
        if not USER_COUPONS:
            markdown_content += "暂无可用优惠券。\n"
        else:
            for coupon in USER_COUPONS:
                markdown_content += f"- **{coupon['title']}**\\\n"
                markdown_content += f"  券码：{coupon['couponCode']}\\\n"
                markdown_content += f"  有效期：{coupon['tradeDateTime']}\\\n"
                
                if coupon.get("products"):
                    product_names = [p["productName"] for p in coupon["products"]]
                    markdown_content += f"  适用商品：{', '.join(product_names)}\\\n"
                
                markdown_content += "\n"
        
        # 构建响应结构
        response = {
            "success": True,
            "code": 200,
            "message": "请求成功",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": markdown_content
        }
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "code": 500,
            "message": f"查询我的优惠券时发生错误: {str(e)}",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": None
        }

def auto_bind_coupons() -> Dict[str, Any]:
    """
    麦麦省一键领券 - 修正版
    参数与麦当劳MCP的auto-bind-coupons完全一致
    
    参数:
      无
    
    返回:
      符合麦当劳MCP统一返回格式的结果
    """
    try:
        # 模拟领取所有可领优惠券
        coupons_to_bind = []
        for coupon in VIRTUAL_COUPONS:
            if coupon["status"] == "未领取":
                coupons_to_bind.append(coupon["title"])
                # 更新状态为已领取（简化逻辑）
                coupon["status"] = "已领取"
        
        if not coupons_to_bind:
            message = "当前没有可领取的优惠券。"
        else:
            coupon_names = "、".join(coupons_to_bind)
            message = f"成功领取优惠券：{coupon_names}"
        
        # 构建响应结构
        response = {
            "success": True,
            "code": 200,
            "message": message,
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": {
                "boundCount": len(coupons_to_bind),
                "boundCoupons": coupons_to_bind
            }
        }
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "code": 500,
            "message": f"一键领券时发生错误: {str(e)}",
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceId": str(uuid.uuid4()),
            "data": None
        }

def _register_tools(register_tool_func):
    """注册本模块的工具到MCP服务器"""
    
    # available-coupons 工具的输入schema
    available_coupons_schema = {
        "type": "object",
        "properties": {},  # 无参数
        "required": []
    }
    
    # query-my-coupons 工具的输入schema
    query_my_coupons_schema = {
        "type": "object",
        "properties": {},  # 无参数
        "required": []
    }
    
    # auto-bind-coupons 工具的输入schema
    auto_bind_coupons_schema = {
        "type": "object",
        "properties": {},  # 无参数
        "required": []
    }
    
    register_tool_func(
        name="available-coupons",
        description="查询用户当前可领取的麦麦省的优惠券列表。返回券名称、图片、状态和促销标签。当用户询问有什么优惠、可以领什么券时使用此工具。",
        input_schema=available_coupons_schema,
        handler=available_coupons
    )
    
    register_tool_func(
        name="query-my-coupons",
        description="查询用户有哪些可用的优惠券。支持用户查看账户下所有优惠券列表。",
        input_schema=query_my_coupons_schema,
        handler=query_my_coupons
    )
    
    register_tool_func(
        name="auto-bind-coupons",
        description="自动领取麦麦省所有当前可用的麦当劳优惠券。无需指定具体的优惠券和couponId，系统会自动领取用户可领的所有券。",
        input_schema=auto_bind_coupons_schema,
        handler=auto_bind_coupons
    )
    
    print("[OK] 注册优惠券工具: available-coupons, query-my-coupons, auto-bind-coupons")

if __name__ == "__main__":
    # 测试代码
    print("测试 coupons_corrected.py 工具模块...")
    
    print("1. 测试 available-coupons:")
    result = available_coupons()
    print(f"成功: {result['success']}")
    print(f"状态码: {result['code']}")
    print(f"消息: {result['message']}")
    if result["success"]:
        print(f"返回数据长度: {len(result['data'])}字符")
        # 打印前200字符
        preview = result['data'][:200] + "..." if len(result['data']) > 200 else result['data']
        print(f"预览: {preview}")
    
    print("\n2. 测试 query-my-coupons:")
    result = query_my_coupons()
    print(f"成功: {result['success']}")
    
    print("\n3. 测试 auto-bind-coupons:")
    result = auto_bind_coupons()
    print(f"成功: {result['success']}")
    if result["success"]:
        data = result["data"]
        print(f"领取数量: {data['boundCount']}")
        print(f"领取的优惠券: {data['boundCoupons']}")