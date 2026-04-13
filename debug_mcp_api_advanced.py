"""
debug_mcp_api_advanced.py - 高级 MCP API 诊断工具

探索 MCP Server 的真实 API 结构
包括 OPTIONS 请求、HEAD 请求、自定义路由等
"""

import requests
import json
import sys
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.DEBUG)

class AdvancedMCPDiagnostics:
    """高级 MCP API 诊断"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
    
    def test_method(self, path: str, method: str, data: Dict = None) -> Dict[str, Any]:
        """测试特定的 HTTP 方法"""
        url = f"{self.base_url}{path}"
        print(f"\n{method:6} {url:60} ", end="", flush=True)
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=3)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data or {}, timeout=3)
            elif method == "HEAD":
                response = requests.head(url, headers=self.headers, timeout=3)
            elif method == "OPTIONS":
                response = requests.options(url, headers=self.headers, timeout=3)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data or {}, timeout=3)
            else:
                print("[X] unsupported")
                return {}
            
            # 显示状态码
            if response.status_code < 300:
                status_str = f"[OK] {response.status_code}"
            elif response.status_code < 400:
                status_str = f"[WARN] {response.status_code}"
            elif response.status_code < 500:
                status_str = f"[FAIL] {response.status_code}"
            else:
                status_str = f"[ERROR] {response.status_code}"
            
            print(status_str)
            
            # 如果返回 2xx 或 3xx，打印响应信息
            if response.status_code < 400:
                try:
                    body = response.json()
                    print(f"     >>> Response: {json.dumps(body)[:100]}")
                except:
                    print(f"     >>> Response: {response.text[:100]}")
                print(f"     >>> Headers: {dict(response.headers)}")
                return {
                    "method": method,
                    "status": response.status_code,
                    "body": response.json() if response.text else None,
                }
            
            return {"method": method, "status": response.status_code}
        except requests.exceptions.Timeout:
            print("[TIMEOUT]")
        except requests.exceptions.ConnectionError:
            print("[CONN_FAIL]")
        except Exception as e:
            print(f"[ERROR] {str(e)[:30]}")
        
        return {}
    
    def discover_advanced(self):
        """高级诊断"""
        print("\n" + "="*100)
        print("高级 MCP API 诊断")
        print("="*100)
        print(f"服务器: {self.base_url}")
        print(f"Token: {self.token[:20]}...")
        
        # 第1步：尝试所有 HTTP 方法到根路径
        print("\n[第1步] 测试所有 HTTP 方法 (到根路径)")
        print("-" * 100)
        for method in ["GET", "POST", "HEAD", "OPTIONS", "PUT"]:
            self.test_method("/", method)
        
        # 第2步：检测服务器信息
        print("\n[第2步] 尝试发现端点列表...")
        print("-" * 100)
        
        discovery_paths = [
            "/openapi.json",      # OpenAPI 规范
            "/swagger.json",      # Swagger 规范
            "/api-docs",          # API 文档
            "/docs",              # 通用文档
            "/-/health",          # 健康检查
            "/api/health",
            "/ping",              # Ping 检查
            "/status",            # 状态
            "/info",              # 信息
            "/.well-known/capabilities",  # MCP 标准
        ]
        
        for path in discovery_paths:
            self.test_method(path, "GET")
        
        # 第3步：尝试 POST 到根路径（可能是 RPC）
        print("\n[第3步] 尝试 RPC 调用...")
        print("-" * 100)
        
        rpc_payloads = [
            {"method": "list-nutrition-foods", "params": {}},
            {"jsonrpc": "2.0", "method": "list-nutrition-foods", "params": {}, "id": 1},
            {"action": "list-nutrition-foods", "data": {}},
        ]
        
        for payload in rpc_payloads:
            print(f"\nPOST / 使用 payload: {json.dumps(payload)}")
            self.test_method("/", "POST", payload)
        
        # 第4步：用下划线替代短横线尝试工具名称
        print("\n[第4步] 尝试不同的工具名称格式...")
        print("-" * 100)
        
        tool_names = [
            "list_nutrition_foods",        # 下划线
            "listNutritionFoods",         # 驼峰
            "ListNutritionFoods",         # 帕斯卡
            "list-nutrition-foods",       # 原始短横线
        ]
        
        for tool_name in tool_names:
            self.test_method(f"/tools/{tool_name}", "POST")
        
        # 第5步：尝试特殊路由
        print("\n[第5步] 尝试 MCP 标准路由...")
        print("-" * 100)
        
        mcp_paths = [
            "/initialize",
            "/call_tool",
            "/list_tools",
            "/resources",
            "/mcp/tools",
            "/mcp/call",
        ]
        
        for path in mcp_paths:
            self.test_method(path, "POST", {"tool": "list-nutrition-foods"})


def main():
    base_url = "https://mcp.mcd.cn"
    token = "iafsHcMfvAEWtcTO6FTtc40jBuAl63VF"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        token = sys.argv[2]
    
    diagnostics = AdvancedMCPDiagnostics(base_url, token)
    diagnostics.discover_advanced()
    
    print("\n" + "="*100)
    print("诊断完成")
    print("="*100)
    print("\n💡 解读结果：")
    print("1. 如果找到 openapi.json 或 swagger.json，可以获取完整的 API 文档")
    print("2. 如果 OPTIONS 返回 2xx，检查 Allow header 了解支持的方法")
    print("3. 如果找到响应为 2xx 的端点，这就是正确的 API")
    print("4. 404 on all paths 可能表示需要特定的认证或网络配置")


if __name__ == "__main__":
    main()
