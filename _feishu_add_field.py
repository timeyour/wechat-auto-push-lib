"""飞书多维表格新增字段。"""
import json

from _feishu_common import BASE, get_feishu_config, get_tenant_access_token, request_json

config = get_feishu_config()
token = get_tenant_access_token(config["app_id"], config["app_secret"])

# 新增字段 - 单选
result = request_json(
    f"{BASE}/bitable/v1/apps/{config['app_token']}/tables/{config['table_id']}/fields",
    token,
    method="POST",
    body={
    "field_name": "排版",
    "type": 3,  # 单选
    "property": {
        "options": [
            {"name": "wenyan"},
            {"name": "direct"},
            {"name": "手动"},
        ]
    }
},
)
print(json.dumps(result, indent=2, ensure_ascii=False))
