"""向飞书多维表格写入一条发布记录。"""
import json
from datetime import datetime

from _feishu_common import BASE, get_feishu_config, get_tenant_access_token, request_json

config = get_feishu_config()
token = get_tenant_access_token(config["app_id"], config["app_secret"])
print("Token OK")

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
result = request_json(
    f"{BASE}/bitable/v1/apps/{config['app_token']}/tables/{config['table_id']}/records",
    token,
    method="POST",
    body={"fields": fields},
)
print(json.dumps(result, indent=2, ensure_ascii=False))
