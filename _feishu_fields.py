"""查看飞书多维表格现有字段"""
import json, urllib.request, urllib.parse, ssl

APP_ID = "cli_a92162aeee799bb6"
APP_SECRET = "DiWHmeD4ZVGpstwfoevB7cA7LwKlDpym"
APP_TOKEN = "GJbsblKx2a6Um7syLR5cO0WNnOg"
TABLE_ID = "tblLYHPmJe6lDxGv"
BASE = "https://open.feishu.cn/open-apis"

ctx = ssl.create_default_context()

# get token
data = urllib.parse.urlencode({"app_id": APP_ID, "app_secret": APP_SECRET}).encode()
req = urllib.request.Request(f"{BASE}/auth/v3/tenant_access_token/internal", data=data, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded")
resp = urllib.request.urlopen(req, context=ctx, timeout=15)
token = json.loads(resp.read())["tenant_access_token"]

# 查看现有字段
req = urllib.request.Request(f"{BASE}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields", method="GET")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, context=ctx, timeout=15)
result = json.loads(resp.read())
fields = result.get("data", {}).get("items", [])
for f in fields:
    print(f"{f['field_id']} | {str(f['type']):15s} | {f['field_name']}")
