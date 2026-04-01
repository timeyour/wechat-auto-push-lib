"""飞书多维表格新增"排版"字段"""
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

# 新增字段 - 单选
body = json.dumps({
    "field_name": "排版",
    "type": 3,  # 单选
    "property": {
        "options": [
            {"name": "wenyan"},
            {"name": "direct"},
            {"name": "手动"},
        ]
    }
}).encode("utf-8")

req = urllib.request.Request(
    f"{BASE}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields",
    data=body,
    method="POST"
)
req.add_header("Authorization", f"Bearer {token}")
req.add_header("Content-Type", "application/json; charset=utf-8")

resp = urllib.request.urlopen(req, context=ctx, timeout=15)
result = json.loads(resp.read())
print(json.dumps(result, indent=2, ensure_ascii=False))
