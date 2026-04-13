"""
test_mcp_standard.py - 按照 MCP 标准握手流程的测试脚本

遵循 MCP JSON-RPC 2.0 协议：
  1. 发送 initialize 请求
  2. 发送 initialized 通知
  3. 查询工具列表
  4. 调用具体工具
"""

import json
import requests
import sys
from typing import Dict, Any, Optional
from datetime import datetime


class MCPStandardClient:
    """MCP 标准 JSON-RPC 2.0 客户端"""

    def __init__(self, base_url: str, token: str):
        """
        初始化 MCP 标准客户端
        
        参数：
          base_url: MCP Server 地址（如 https://mcp.mcd.cn）
          token: 认证 token
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.request_id = 0
        self.session = None
        
        print("="*80)
        print("MCP 标准握手流程测试")
        print("="*80)
        print(f"MCP Server: {self.base_url}")
        print(f"Token: {token[:20]}..." if len(token) > 20 else f"Token: {token}")
        print()

    def _get_next_id(self) -> int:
        """获取下一个请求 ID"""
        self.request_id += 1
        return self.request_id

    def _send_jsonrpc(self, method: str, params: Dict = None, expect_response: bool = True) -> Optional[Dict]:
        """
        发送 JSON-RPC 2.0 请求
        
        参数：
          method: RPC 方法名
          params: 方法参数
          expect_response: 是否期望响应（notifications 不期望响应）
        
        返回：
          响应数据（如果期望响应）
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
        }
        
        if expect_response:
            request_id = self._get_next_id()
            request_data["id"] = request_id
        
        if params:
            request_data["params"] = params
        
        try:
            print(f"➜ 发送 {method}")
            print(f"   请求体: {json.dumps(request_data, indent=2, ensure_ascii=False)[:200]}...")
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=request_data,
                timeout=30,
            )
            
            print(f"   状态码: {response.status_code}")
            
            if not expect_response:
                print(f"✓ {method} 通知已发送\n")
                return None
            
            # 解析响应
            try:
                result = response.json()
                print(f"   响应: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
                
                if "error" in result:
                    print(f"✗ {method} 失败: {result['error']}\n")
                    return None
                
                print(f"✓ {method} 成功\n")
                return result.get("result")
            except json.JSONDecodeError:
                print(f"   响应文本: {response.text[:200]}")
                print(f"✗ {method} 响应解析失败\n")
                return None
                
        except Exception as e:
            print(f"✗ {method} 请求失败: {e}\n")
            return None

    def step1_initialize(self) -> bool:
        """
        第一步：发送 initialize 请求
        建立 MCP 会话，协商协议版本和能力
        """
        print("-" * 80)
        print("【第一步】发送 initialize 请求")
        print("-" * 80)
        
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-test-client",
                "version": "1.0.0"
            }
        }
        
        result = self._send_jsonrpc("initialize", params)
        return result is not None

    def step2_initialized(self) -> bool:
        """
        第二步：发送 initialized 通知
        告知服务器客户端已初始化完成，可以开始接收服务器通知
        """
        print("-" * 80)
        print("【第二步】发送 initialized 通知")
        print("-" * 80)
        
        self._send_jsonrpc("notifications/initialized", expect_response=False)
        return True

    def step3_list_tools(self) -> Optional[list]:
        """
        第三步：查询工具列表
        这是最关键的一步，用来获取 MCP Server 提供的所有工具
        """
        print("-" * 80)
        print("【第三步】查询工具列表 (tools/list)")
        print("-" * 80)
        
        result = self._send_jsonrpc("tools/list", {})
        
        if result and "tools" in result:
            tools = result["tools"]
            print(f"📋 找到 {len(tools)} 个工具:\n")
            for i, tool in enumerate(tools, 1):
                print(f"  {i}. {tool.get('name', 'unknown')}")
                if "description" in tool:
                    print(f"     描述: {tool['description'][:60]}...")
                if "inputSchema" in tool:
                    params = tool["inputSchema"].get("properties", {})
                    param_names = ", ".join(params.keys())
                    print(f"     参数: {param_names if param_names else '(无参)'}")
                print()
            return tools
        
        return None

    def call_tool(self, tool_name: str, tool_input: Dict = None, show_output: bool = True) -> Optional[Any]:
        """
        调用指定的工具
        
        参数：
          tool_name: 工具名称
          tool_input: 工具输入参数（默认为空字典）
          show_output: 是否显示详细输出
        """
        if tool_input is None:
            tool_input = {}
        
        if show_output:
            print("-" * 80)
            print(f"【调用工具】{tool_name}")
            print("-" * 80)
        
        params = {
            "name": tool_name,
            "arguments": tool_input
        }
        
        result = self._send_jsonrpc("tools/call", params) if show_output else self._call_tool_silent(tool_name, tool_input)
        return result

    def _call_tool_silent(self, tool_name: str, tool_input: Dict) -> Optional[Any]:
        """
        静默调用工具（不显示详细请求过程）
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        
        request_id = self._get_next_id()
        request_data = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": tool_input
            }
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=request_data,
                timeout=30,
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("result")
            else:
                return None
        except Exception:
            return None

    def batch_test_no_param_tools(self, tools: list) -> Dict[str, Any]:
        """
        批量测试不需要参数的工具
        
        参数：
          tools: 工具列表（来自 tools/list）
        
        返回：
          测试结果字典
        """
        print("\n" + "="*80)
        print("【批量测试】无参数工具测试")
        print("="*80 + "\n")
        
        # 找出所有无参工具
        no_param_tools = []
        for tool in tools:
            if "inputSchema" in tool:
                properties = tool["inputSchema"].get("properties", {})
                if not properties:  # 无参数
                    no_param_tools.append(tool)
        
        print(f"找到 {len(no_param_tools)} 个无参数工具:\n")
        
        results = {
            "total": len(no_param_tools),
            "success": 0,
            "failed": 0,
            "tools": {}
        }
        
        # 测试每个无参工具
        for i, tool in enumerate(no_param_tools, 1):
            tool_name = tool.get("name", "unknown")
            description = tool.get("description", "")[:50]
            
            print(f"[{i}/{len(no_param_tools)}] 测试 {tool_name}... ", end="", flush=True)
            
            try:
                result = self.call_tool(tool_name, {}, show_output=False)
                
                if result is not None:
                    print("✓ 成功")
                    results["success"] += 1
                    results["tools"][tool_name] = {
                        "status": "SUCCESS",
                        "description": description,
                        "result_preview": str(result)[:100] if result else None
                    }
                else:
                    print("✗ 失败（返回 None）")
                    results["failed"] += 1
                    results["tools"][tool_name] = {
                        "status": "FAILED",
                        "description": description,
                        "error": "返回值为 None"
                    }
            except Exception as e:
                print(f"✗ 异常: {str(e)[:50]}")
                results["failed"] += 1
                results["tools"][tool_name] = {
                    "status": "ERROR",
                    "description": description,
                    "error": str(e)
                }
        
        # 打印摘要
        print("\n" + "-" * 80)
        print("测试摘要")
        print("-" * 80)
        print(f"总数: {results['total']}")
        print(f"成功: {results['success']} ✓")
        print(f"失败: {results['failed']} ✗")
        print(f"成功率: {(results['success']/results['total']*100):.1f}%")
        
        # 打印失败的工具
        if results["failed"] > 0:
            print("\n失败的工具:")
            for tool_name, info in results["tools"].items():
                if info["status"] != "SUCCESS":
                    print(f"  - {tool_name}: {info.get('error', 'Unknown error')}")
        
        return results

    def run_full_handshake(self):
        """执行完整的握手流程"""
        print("\n")
        
        # 第一步：initialize
        if not self.step1_initialize():
            print("❌ Initialize 失败，无法继续")
            return False
        
        # 第二步：initialized
        if not self.step2_initialized():
            print("❌ Initialized 失败，无法继续")
            return False
        
        # 第三步：tools/list
        tools = self.step3_list_tools()
        if tools is None:
            print("❌ Tools/list 失败，无法继续")
            return False
        
        print("="*80)
        print("✅ MCP 握手流程完成！")
        print("="*80)
        print(f"\n可用工具总数: {len(tools)}")
        
        return True


def main():
    """主程序"""
    
    # 配置 MCP Server 信息
    MCP_SERVER = "https://mcp.mcd.cn"
    MCP_TOKEN = "iafsHcMfvAEWtcTO6FTtc40jBuAl63VF"
    
    # 创建客户端
    client = MCPStandardClient(base_url=MCP_SERVER, token=MCP_TOKEN)
    
    # 执行握手流程
    success = client.run_full_handshake()
    
    if success:
        # 获取工具列表用于后续测试
        tools = []
        print("\n" + "="*80)
        print("【再次】查询工具列表（用于获取详细信息）")
        print("="*80 + "\n")
        
        # 静默查询工具列表
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MCP_TOKEN}",
        }
        
        request_data = {
            "jsonrpc": "2.0",
            "id": client._get_next_id(),
            "method": "tools/list",
            "params": {}
        }
        
        try:
            response = requests.post(
                MCP_SERVER,
                headers=headers,
                json=request_data,
                timeout=30,
            )
            if response.status_code == 200:
                result = response.json()
                tools = result.get("result", {}).get("tools", [])
        except:
            pass
        
        if tools:
            # 执行无参工具批量测试
            batch_results = client.batch_test_no_param_tools(tools)
            
            # 保存结果到文件
            output_file = "mcp_no_param_test_results.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(batch_results, f, indent=2, ensure_ascii=False)
            print(f"\n💾 测试结果已保存到: {output_file}\n")
        else:
            print("⚠️ 无法获取工具列表，跳过批量测试\n")
        
        # 演示单个工具详细调用
        print("="*80)
        print("【示例】详细调用 query-my-account 工具")
        print("="*80 + "\n")
        
        result = client.call_tool("query-my-account", {}, show_output=True)
        
        if result:
            print(f"\n✓ 工具调用成功")
            output = json.dumps(result, indent=2, ensure_ascii=False)
            print(f"结果（前 500 字）:\n{output[:500]}...")
        else:
            print(f"\n✗ 工具调用失败")
    else:
        print("\n❌ 握手流程失败，请检查：")
        print("  1. MCP Server 地址是否正确")
        print("  2. 认证 Token 是否有效")
        print("  3. 网络连接是否正常")


if __name__ == "__main__":
    main()
