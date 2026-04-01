"""直接调API写入Claude Code文章记录"""
import json, urllib.request, urllib.parse, ssl
from datetime import datetime

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
print(f"Token OK")

ts = int(datetime(2026, 3, 31).timestamp() * 1000)
fields = {
    "标题": "Anthropic又双叒叕把源码发到npm上了：51万行Claude Code代码泄露始末",
    "发布日期": ts,
    "选题类型": "热点解读",
    "预估字数": 2800,
    "封面类型": "AI生成",
    "标题关键词": "Anthropic,Claude Code,源码泄露,npm,source map",
    "状态": "草稿",
    "阅读量": 0,
    "推荐率": 0,
    "完读率": 0,
    "GEO评分": 8,
    "排版": "wenyan",
    "备注": "豆包4.0生图，pie主题，v2重做图片",
}

body = json.dumps({"fields": fields}).encode("utf-8")
req = urllib.request.Request(
    f"{BASE}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records",
    data=body,
    method="POST"
)
req.add_header("Authorization", f"Bearer {token}")
req.add_header("Content-Type", "application/json; charset=utf-8")

try:
    resp = urllib.request.urlopen(req, context=ctx, timeout=15)
    result = json.loads(resp.read())
    print(json.dumps(result, indent=2, ensure_ascii=False))
except urllib.error.HTTPError as e:
    err_body = e.read().decode("utf-8", errors="replace")
    print(f"HTTP {e.code}")
    print(err_body)
