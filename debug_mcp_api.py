"""
debug_mcp_api.py - MCP Server API 诊断工具

用于调试和发现正确的 MCP Server API 端点
"""

import requests
import json
import sys
from typing import Dict, Any

class MCPAPIDiagnostics:
    """MCP API 诊断工具"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
    
    def test_endpoint(self, path: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """测试单个端点"""
        url = f"{self.base_url}{path}"
        print(f"\n{'='*80}")
        print(f"测试: {method} {url}")
        print(f"{'='*80}")
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=5)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data or {}, timeout=5)
            else:
                return {"status": "UNKNOWN", "error": f"不支持的方法: {method}"}
            
            result = {
                "status_code": response.status_code,
                "status": "✓ 成功" if response.status_code < 400 else "✗ 失败",
                "headers": dict(response.headers),
            }
            
            try:
                result["body"] = response.json()
            except:
                result["body"] = response.text[:200]
            
            # 漂亮打印结果
            print(f"状态码: {response.status_code}")
            print(f"响应体: {json.dumps(result['body'], indent=2, ensure_ascii=False)[:500]}")
            
            return result
        except requests.exceptions.RequestException as e:
            print(f"✗ 请求失败: {e}")
            return {"status": "ERROR", "error": str(e)}
    
    def discover_api(self):
        """尝试发现 MCP Server 的 API 结构"""
        
        print("\n" + "="*80)
        print("开始诊断 MCP Server API")
        print("="*80)
        print(f"Server: {self.base_url}")
        
        # 测试根路径
        print("\n[第1步] 测试根路径...")
        self.test_endpoint("/")
        
        # 测试常见的 API 路径
        print("\n[第2步] 尝试常见的 API 查询方法...")
        
        common_paths = [
            "/tools",           # 列出所有工具
            "/api/tools",       # 带 api 前缀
            "/v1/tools",        # API 版本前缀
            "/capabilities",    # 能力查询
            "/api",             # API 根路径
            "/health",          # 健康检查
        ]
        
        for path in common_paths:
            self.test_endpoint(path)
        
        # 测试工具调用的不同格式
        print("\n[第3步] 尝试工具调用的不同 API 格式...")
        
        test_tool = "list-nutrition-foods"
        test_payload = {}
        
        tool_paths = [
            ("/tools/list-nutrition-foods", "POST"),
            ("/api/tools/list-nutrition-foods", "POST"),
            ("/v1/tools/list-nutrition-foods", "POST"),
            ("/tools/get", "POST"),  # POST with tool name in body
            ("/invoke", "POST"),     # Generic invoke endpoint
            ("/api/invoke", "POST"),
        ]
        
        for path, method in tool_paths:
            if "{tool_name}" in path:
                path = path.replace("{tool_name}", test_tool)
            self.test_endpoint(path, method=method, data=test_payload)
    
    def inspect_response_headers(self, path: str = "/"):
        """检查响应头来找出 API 信息"""
        print("\n[第4步] 检查响应头寻找 API 信息...")
        try:
            response = requests.get(
                f"{self.base_url}{path}",
                headers=self.headers,
                timeout=5
            )
            print("\n响应头:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
        except Exception as e:
            print(f"✗ 无法获取响应头: {e}")


def main():
    # MCP Server 配置
    base_url = "https://mcp.mcd.cn"
    token = "iafsHcMfvAEWtcTO6FTtc40jBuAl63VF"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        token = sys.argv[2]
    
    print("\n💡 MCP Server API 诊断工具")
    print(f"目标服务器: {base_url}")
    print(f"Token: {token[:20]}...")
    
    diagnostics = MCPAPIDiagnostics(base_url, token)
    diagnostics.discover_api()
    diagnostics.inspect_response_headers()
    
    print("\n" + "="*80)
    print("诊断完成")
    print("="*80)
    print("\n📝 根据诊断结果，请检查：")
    print("1. 是否找到了成功的端点（状态码 200-299）")
    print("2. 响应体中是否包含工具列表或 API 文档")
    print("3. 根据实际的 API 格式，更新 mcp_client.py 中的 call_tool 方法")


if __name__ == "__main__":
    main()
