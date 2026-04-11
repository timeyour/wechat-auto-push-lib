"""飞书多维表格通用配置与请求封装。"""
import json
import os
import ssl
import urllib.parse
import urllib.request

BASE = "https://open.feishu.cn/open-apis"
CTX = ssl.create_default_context()


def get_feishu_config() -> dict:
    config = {
        "app_id": os.getenv("FEISHU_APP_ID", ""),
        "app_secret": os.getenv("FEISHU_APP_SECRET", ""),
        "app_token": os.getenv("FEISHU_BITABLE_APP_TOKEN", ""),
        "table_id": os.getenv("FEISHU_BITABLE_TABLE_ID", ""),
    }
    missing = [key for key, value in config.items() if not value]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            "缺少飞书多维表格配置，请在 .env 中补齐: "
            f"{joined}"
        )
    return config


def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    data = urllib.parse.urlencode({
        "app_id": app_id,
        "app_secret": app_secret,
    }).encode()
    req = urllib.request.Request(
        f"{BASE}/auth/v3/tenant_access_token/internal",
        data=data,
        method="POST",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    resp = urllib.request.urlopen(req, context=CTX, timeout=15)
    return json.loads(resp.read())["tenant_access_token"]


def request_json(url: str, token: str, method: str = "GET", body: dict | None = None) -> dict:
    payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if payload is not None:
        req.add_header("Content-Type", "application/json; charset=utf-8")
    resp = urllib.request.urlopen(req, context=CTX, timeout=15)
    return json.loads(resp.read())
