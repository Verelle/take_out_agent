#!/usr/bin/env python3
"""
虚拟门店MCP Server - 兼容版
兼容真实麦当劳MCP的Streamable HTTP协议
基于FastAPI实现，支持JSON-RPC 2.0和流式HTTP响应
"""

import json
import logging
import time
from typing import Dict, Any, Callable, Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="虚拟门店MCP Server (兼容版)",
    description="BridgeX项目虚拟门店MCP服务 - 兼容真实麦当劳MCP的Streamable HTTP协议",
    version="1.0.0"
)

# 添加CORS中间件（允许跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 工具注册表：方法名 -> {"schema": ..., "handler": ...}
tools_registry = {}

def register_tool(name: str, description: str, input_schema: Dict[str, Any], handler: Callable):
    """注册工具到MCP服务器"""
    tools_registry[name] = {
        "name": name,
        "description": description,
        "inputSchema": input_schema,
        "handler": handler
    }
    logger.info(f"注册工具: {name}")

def import_and_register_corrected_tools():
    """导入所有修正版工具模块并注册工具"""
    logger.info("导入修正版工具模块...")
    
    # 导入修正版门店工具
    try:
        from tools.stores_corrected import _register_tools as register_store_tools
        register_store_tools(register_tool)
        logger.info("[OK] 修正版门店工具注册完成")
    except ImportError as e:
        logger.error(f"导入修正版门店工具失败: {e}")
    
    # 导入修正版菜单工具
    try:
        from tools.menu_corrected import _register_tools as register_menu_tools
        register_menu_tools(register_tool)
        logger.info("[OK] 修正版菜单工具注册完成")
    except ImportError as e:
        logger.error(f"导入修正版菜单工具失败: {e}")
    
    # 导入修正版价格工具
    try:
        from tools.pricing_corrected import _register_tools as register_pricing_tools
        register_pricing_tools(register_tool)
        logger.info("[OK] 修正版价格工具注册完成")
    except ImportError as e:
        logger.error(f"导入修正版价格工具失败: {e}")
    
    # 导入修正版订单工具
    try:
        from tools.orders_corrected import _register_tools as register_order_tools
        register_order_tools(register_tool)
        logger.info("[OK] 修正版订单工具注册完成")
    except ImportError as e:
        logger.error(f"导入修正版订单工具失败: {e}")
    
    # 导入修正版优惠券工具
    try:
        from tools.coupons_corrected import _register_tools as register_coupon_tools
        register_coupon_tools(register_tool)
        logger.info("[OK] 修正版优惠券工具注册完成")
    except ImportError as e:
        logger.error(f"导入修正版优惠券工具失败: {e}")
    
    logger.info(f"共注册 {len(tools_registry)} 个工具")
    logger.info(f"已注册工具: {list(tools_registry.keys())}")

@app.post("/")
async def handle_jsonrpc(request: Request):
    """
    处理JSON-RPC 2.0请求
    兼容真实麦当劳MCP的Streamable HTTP协议
    """
    try:
        # 检查是否为流式请求
        transfer_encoding = request.headers.get("transfer-encoding", "")
        accept = request.headers.get("accept", "")
        
        # 读取请求体
        body = await request.body()
        
        # 解析JSON
        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            return JSONResponse({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error: Invalid JSON"
                },
                "id": None
            }, status_code=400)
    except Exception as e:
        logger.error(f"读取请求失败: {e}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {
                "code": -32600,
                "message": f"Invalid Request: {str(e)}"
            },
            "id": None
        }, status_code=400)
    
    # 验证JSON-RPC 2.0基本结构
    if data.get("jsonrpc") != "2.0":
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {
                "code": -32600,
                "message": "Invalid Request: jsonrpc must be exactly '2.0'"
            },
            "id": data.get("id")
        }, status_code=400)
    
    method = data.get("method")
    params = data.get("params", {})
    request_id = data.get("id")
    
    logger.info(f"收到请求: method={method}, id={request_id}, transfer-encoding={transfer_encoding}")
    
    # 处理MCP标准方法
    if method == "initialize":
        return handle_initialize(request_id, params)
    elif method == "notifications/initialized":
        return handle_initialized(request_id, params)
    elif method == "tools/list":
        return handle_tools_list(request_id, params)
    elif method == "tools/call":
        return handle_tools_call(request_id, params, stream_mode=(transfer_encoding == "chunked"))
    elif method in tools_registry:
        return handle_tool_call(method, request_id, params, stream_mode=(transfer_encoding == "chunked"))
    else:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            },
            "id": request_id
        }, status_code=404)

@app.post("/stream")
async def handle_stream_request(request: Request):
    """
    处理流式请求端点
    专为Streamable HTTP设计
    """
    # 设置流式响应头
    headers = {
        "Transfer-Encoding": "chunked",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    
    # 转发到主处理函数，但标记为流式模式
    # 这里我们复制请求体并手动调用handle_jsonrpc
    try:
        body = await request.body()
        data = json.loads(body.decode('utf-8'))
        
        method = data.get("method")
        params = data.get("params", {})
        request_id = data.get("id")
        
        logger.info(f"收到流式请求: method={method}, id={request_id}")
        
        # 处理工具调用（流式模式）
        if method == "tools/call":
            return handle_tools_call(request_id, params, stream_mode=True)
        elif method in tools_registry:
            return handle_tool_call(method, request_id, params, stream_mode=True)
        else:
            # 其他方法也支持流式
            return await handle_jsonrpc(request)
            
    except Exception as e:
        logger.error(f"处理流式请求失败: {e}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {
                "code": -32600,
                "message": f"Invalid Request: {str(e)}"
            },
            "id": None
        }, status_code=400)

def handle_initialize(request_id, params):
    """处理initialize请求（MCP握手第一步）"""
    logger.info("处理initialize请求")
    
    response = {
        "jsonrpc": "2.0",
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "virtual-store-mcp-server-corrected",
                "version": "1.0.0"
            }
        },
        "id": request_id
    }
    
    return JSONResponse(response)

def handle_initialized(request_id, params):
    """处理notifications/initialized请求（MCP握手第二步）"""
    logger.info("处理notifications/initialized请求")
    # 根据MCP规范，这是通知（notification），不需要响应结果
    # 但为了兼容性，返回空结果
    return JSONResponse({
        "jsonrpc": "2.0",
        "result": None,
        "id": request_id
    })

def handle_tools_list(request_id, params):
    """处理tools/list请求，返回所有注册的工具"""
    logger.info("处理tools/list请求")
    
    tools_list = []
    for tool_name, tool_info in tools_registry.items():
        tools_list.append({
            "name": tool_info["name"],
            "description": tool_info["description"],
            "inputSchema": tool_info["inputSchema"]
        })
    
    response = {
        "jsonrpc": "2.0",
        "result": {
            "tools": tools_list
        },
        "id": request_id
    }
    
    return JSONResponse(response)

def handle_tools_call(request_id, params, stream_mode=False):
    """处理标准的tools/call请求（真实麦当劳MCP使用）"""
    logger.info(f"处理tools/call请求 (stream_mode={stream_mode})")
    
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    if not tool_name:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {
                "code": -32602,
                "message": "Invalid params: missing 'name' field"
            },
            "id": request_id
        }, status_code=400)
    
    # 调用对应的工具
    return handle_tool_call(tool_name, request_id, arguments, stream_mode)

def handle_tool_call(method, request_id, params, stream_mode=False):
    """处理工具调用请求"""
    logger.info(f"处理工具调用: {method} (stream_mode={stream_mode})")
    
    tool_info = tools_registry.get(method)
    if not tool_info:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            },
            "id": request_id
        }, status_code=404)
    
    try:
        # 调用工具处理函数
        result = tool_info["handler"](**params)
        
        # 工具返回的result应该已经是麦当劳标准格式
        # 直接包装为JSON-RPC响应
        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
        
        # 流式模式：使用StreamingResponse
        if stream_mode:
            async def generate_stream():
                # 将响应转换为JSON字符串
                response_json = json.dumps(response, ensure_ascii=False)
                yield response_json
            
            return StreamingResponse(
                generate_stream(),
                media_type="application/json",
                headers={
                    "Transfer-Encoding": "chunked",
                    "Cache-Control": "no-cache",
                }
            )
        else:
            # 非流式模式：普通JSONResponse
            return JSONResponse(response)
        
    except Exception as e:
        logger.error(f"工具调用失败: {method}, error: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error in tool {method}: {str(e)}"
            },
            "id": request_id
        }
        
        if stream_mode:
            async def generate_error_stream():
                yield json.dumps(error_response, ensure_ascii=False)
            
            return StreamingResponse(
                generate_error_stream(),
                media_type="application/json",
                headers={
                    "Transfer-Encoding": "chunked",
                    "Cache-Control": "no-cache",
                }
            )
        else:
            return JSONResponse(error_response, status_code=500)

# 启动时注册工具
import_and_register_corrected_tools()

@app.get("/")
async def root():
    """根路径，返回服务器信息"""
    return {
        "name": "虚拟门店MCP Server (兼容版)",
        "version": "1.0.0",
        "description": "兼容真实麦当劳MCP的Streamable HTTP协议的虚拟门店服务",
        "protocol": "JSON-RPC 2.0 with Streamable HTTP support",
        "endpoints": {
            "jsonrpc": "/",
            "stream": "/stream",
            "health": "/health"
        },
        "tools_count": len(tools_registry),
        "tools": list(tools_registry.keys())
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "protocol": "JSON-RPC 2.0 with Streamable HTTP",
        "streaming_support": True,
        "tools_registered": len(tools_registry)
    }

@app.get("/protocol")
async def protocol_info():
    """返回协议信息"""
    return {
        "protocol": "JSON-RPC 2.0",
        "streamable_http": True,
        "transfer_encoding": "chunked",
        "endpoints": {
            "standard": "/",
            "streaming": "/stream"
        },
        "authentication": "Bearer token"
    }

if __name__ == "__main__":
    logger.info("启动虚拟门店MCP Server (兼容版)...")
    logger.info(f"已注册工具: {list(tools_registry.keys())}")
    logger.info("协议: JSON-RPC 2.0 with Streamable HTTP support")
    logger.info("标准端点: http://0.0.0.0:8000/")
    logger.info("流式端点: http://0.0.0.0:8000/stream")
    logger.info("健康检查: http://0.0.0.0:8000/health")
    logger.info("协议信息: http://0.0.0.0:8000/protocol")
    
    # 启动服务器，配置支持流式传输
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        # 启用分块传输编码支持
        proxy_headers=True,
        # 设置较长的keep-alive超时
        timeout_keep_alive=30
    )