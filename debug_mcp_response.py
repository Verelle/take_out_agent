"""
debug_mcp_response.py - Debug MCP Server responses in detail
"""

import requests
import json

def test_mcp():
    base_url = "https://mcp.mcd.cn"
    token = "iafsHcMfvAEWtcTO6FTtc40jBuAl63VF"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    
    # Test 1: Empty request
    print("\n[TEST 1] Empty JSON-RPC request:")
    payload = {
        "jsonrpc": "2.0",
        "method": "",
        "params": {},
        "id": 1,
    }
    response = requests.post(base_url, headers=headers, json=payload, timeout=3)
    print(f"Status: {response.status_code}")
    print(f"Body: '{response.text}' (length: {len(response.text)})")
    if response.text:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Test 2: version method
    print("\n[TEST 2] Try 'version' method:")
    payload = {
        "jsonrpc": "2.0",
        "method": "version",
        "params": {},
        "id": 1,
    }
    response = requests.post(base_url, headers=headers, json=payload, timeout=3)
    print(f"Status: {response.status_code}")
    print(f"Body: '{response.text[:200]}'")
    if response.text:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Test 3: info method
    print("\n[TEST 3] Try 'info' method:")
    payload = {
        "jsonrpc": "2.0",
        "method": "info",
        "params": {},
        "id": 1,
    }
    response = requests.post(base_url, headers=headers, json=payload, timeout=3)
    print(f"Status: {response.status_code}")
    print(f"Body: '{response.text[:200]}'")
    if response.text:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Test 4: Simple call with params
    print("\n[TEST 4] Try 'listNutritionFoods' with params:")
    payload = {
        "jsonrpc": "2.0",
        "method": "listNutritionFoods",
        "params": {"foodName": ""},
        "id": 1,
    }
    response = requests.post(base_url, headers=headers, json=payload, timeout=3)
    print(f"Status: {response.status_code}")
    print(f"Body: '{response.text[:200]}'")
    if response.text:
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except:
            pass
    
    # Check headers
    print("\n[RESPONSE HEADERS from POST /]:")
    payload = {"jsonrpc": "2.0", "method": "test", "params": {}, "id": 1}
    response = requests.post(base_url, headers=headers, json=payload, timeout=3)
    for key, value in response.headers.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    test_mcp()
