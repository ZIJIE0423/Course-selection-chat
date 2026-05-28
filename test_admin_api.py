import requests
import json

BASE_URL = "http://localhost:8001"


# 1. 获取待审核内容
print("=== 1. 获取待审核内容 ===")
pending_response = requests.get(f"{BASE_URL}/api/v1/admin/crawled/pending")
print(f"Status code: {pending_response.status_code}")
if pending_response.status_code == 200:
    data = pending_response.json()
    print(f"Total pending documents: {data['total']}")
    if data['data']:
        print("First document:")
        print(json.dumps(data['data'][0], indent=2, ensure_ascii=False))
else:
    print(f"Error: {pending_response.text}")


# 2. 选择第一个待审核文档进行测试 (如果存在)
if pending_response.status_code == 200 and data['data']:
    doc_id = data['data'][0]['id']
    
    # 3. 审核通过
    print("\n=== 2. 审核通过 ===")
    approve_response = requests.post(f"{BASE_URL}/api/v1/admin/crawled/{doc_id}/approve")
    print(f"Status code: {approve_response.status_code}")
    print(f"Response: {approve_response.json()}")
    
    # 4. 触发索引更新
    print("\n=== 3. 触发索引更新 ===")
    index_response = requests.post(f"{BASE_URL}/api/v1/admin/crawled/{doc_id}/index")
    print(f"Status code: {index_response.status_code}")
    print(f"Response: {index_response.json()}")
    
    # 5. 驳回测试（确保文档状态正确）
    print("\n=== 4. 驳回测试 ===")
    reject_response = requests.post(f"{BASE_URL}/api/v1/admin/crawled/{doc_id}/reject")
    print(f"Status code: {reject_response.status_code}")
    print(f"Response: {reject_response.json()}")
else:
    print("No pending documents to test")