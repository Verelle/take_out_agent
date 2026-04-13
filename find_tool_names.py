"""
find_tool_names.py - Discover correct MCP tool names

Try different naming formats to find which tools are supported
"""

import requests
import json

class ToolNameFinder:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
    
    def try_list_tools(self):
        method_names = [
            "listTools",
            "list_tools",
            "list-tools",
            "tools",
            "Tools",
        ]
        
        print("\nTrying different ways to list tools...")
        print("-" * 100)
        
        for method in method_names:
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": {},
                "id": 1,
            }
            
            try:
                print(f"Trying method: {method:20} ... ", end="", flush=True)
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=3,
                )
                result = response.json()
                
                if "error" in result and result["error"] is not None:
                    print(f"ERROR: {result['error'].get('message', 'unknown')[:50]}")
                elif "result" in result:
                    print(f"SUCCESS!")
                    print(f"  Response: {json.dumps(result['result'], indent=2)[:500]}")
                    return result.get("result")
            except Exception as e:
                print(f"FAILED: {str(e)[:50]}")
        
        print("\nTrying direct tool invocations...")
        print("-" * 100)
        
        tool_names = [
            "listNutritionFoods",
            "queryNearbyStores",
            "queryMeals",
            "queryMealDetail",
            "calculatePrice",
            "createOrder",
            "queryOrder",
            "campaignCalendar",
            "availableCoupons",
            "autoBindCoupons",
            "queryMyCoupons",
            "queryMyAccount",
            "mallPointsProducts",
            "mallProductDetail",
            "mallCreateOrder",
            "nowTimeInfo",
            "list_nutrition_foods",
            "query_nearby_stores",
            "query_meals",
            "query_meal_detail",
            "calculate_price",
            "create_order",
            "query_order",
            "campaign_calendar",
            "available_coupons",
            "auto_bind_coupons",
            "query_my_coupons",
            "query_my_account",
            "mall_points_products",
            "mall_product_detail",
            "mall_create_order",
            "now_time_info",
        ]
        
        found_tools = []
        
        for tool_name in tool_names:
            payload = {
                "jsonrpc": "2.0",
                "method": tool_name,
                "params": {},
                "id": 1,
            }
            
            try:
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=2,
                )
                
                result = response.json()
                
                if "error" in result and result["error"] is not None:
                    error_code = result["error"].get("code", 0)
                    error_msg = result["error"].get("message", "")
                    
                    if error_code == -32601:
                        pass
                    else:
                        print(f"  {tool_name:30} - RECOGNIZED! Error: {error_msg[:40]}")
                        found_tools.append(tool_name)
                elif "result" in result:
                    print(f"  {tool_name:30} - SUCCESS!")
                    found_tools.append(tool_name)
            except:
                pass
        
        if found_tools:
            print(f"\n[FOUND VALID TOOLS]")
            for tool in found_tools:
                print(f"  - {tool}")
        else:
            print("\nNo valid tools found.")


def main():
    base_url = "https://mcp.mcd.cn"
    token = "iafsHcMfvAEWtcTO6FTtc40jBuAl63VF"
    
    finder = ToolNameFinder(base_url, token)
    finder.try_list_tools()


if __name__ == "__main__":
    main()
