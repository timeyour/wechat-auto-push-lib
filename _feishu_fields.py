"""查看飞书多维表格现有字段。"""
from _feishu_common import BASE, get_feishu_config, get_tenant_access_token, request_json

config = get_feishu_config()
token = get_tenant_access_token(config["app_id"], config["app_secret"])
result = request_json(
    f"{BASE}/bitable/v1/apps/{config['app_token']}/tables/{config['table_id']}/fields",
    token,
)
fields = result.get("data", {}).get("items", [])
for f in fields:
    print(f"{f['field_id']} | {str(f['type']):15s} | {f['field_name']}")
