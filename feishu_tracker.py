"""
飞书多维表格 - 公众号文章指标追踪工具

用法:
  # 记录一篇新文章（写入发布指标）
  python feishu_tracker.py add --title "文章标题" --type "热点解读" --words 2800 --cover "AI生成" --keywords "AI,Agent" --status "已发布" --geo 8

  # 查看最近记录
  python feishu_tracker.py list [--limit 10]

  # 更新阅读数据（发布后手动补）
  python feishu_tracker.py update --record-id recvfruJ59qloO --reads 1500 --recommend 88 --finish 72
"""
import urllib.request
import urllib.parse
import json
import ssl
import sys
import argparse
import os
import time
from datetime import datetime

# ─── 配置 ───────────────────────────────────────────
APP_ID = os.environ.get("FEISHU_APP_ID", "cli_a92162aeee799bb6")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "DiWHmeD4ZVGpstwfoevB7cA7LwKlDpym")
APP_TOKEN = "GJbsblKx2a6Um7syLR5cO0WNnOg"
TABLE_NAME = "文章记录"
BASE = "https://open.feishu.cn/open-apis"
# ─────────────────────────────────────────────────────

ctx = ssl.create_default_context()
_token_cache = {"token": "", "expire": 0}


def _log(msg):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(msg, flush=True)
    except Exception:
        try:
            with open(r"c:\Users\lixin\WorkBuddy\Claw\_feishu_log.txt", "a", encoding="utf-8") as f:
                f.write(str(msg) + "\n")
        except Exception:
            pass


def _api(method, path, body=None, token=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"code": -1, "msg": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}"}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def get_token():
    if _token_cache["token"] and time.time() < _token_cache["expire"]:
        return _token_cache["token"]
    data = urllib.parse.urlencode({"app_id": APP_ID, "app_secret": APP_SECRET}).encode()
    url = f"{BASE}/auth/v3/tenant_access_token/internal"
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    resp = urllib.request.urlopen(req, context=ctx, timeout=15)
    result = json.loads(resp.read().decode("utf-8"))
    if result.get("code") != 0:
        raise RuntimeError(f"获取token失败: {result.get('msg')}")
    _token_cache["token"] = result["tenant_access_token"]
    _token_cache["expire"] = time.time() + 6800  # ~113min
    return _token_cache["token"]


def get_table_id(token):
    result = _api("GET", f"/bitable/v1/apps/{APP_TOKEN}/tables", token=token)
    for t in result.get("data", {}).get("items", []):
        if t.get("name") == TABLE_NAME:
            return t["table_id"]
    raise RuntimeError(f"找不到表 '{TABLE_NAME}'，请检查飞书多维表格")


def add_record(title, article_type="", words=0, cover="", keywords="",
               status="草稿", geo=0, note="", publish_date=None, layout="", reads=0):
    """写入一条文章记录"""
    token = get_token()
    table_id = get_table_id(token)

    fields = {"标题": title}
    if publish_date:
        ts = int(datetime.strptime(publish_date, "%Y-%m-%d").timestamp() * 1000)
        fields["发布日期"] = ts
    else:
        fields["发布日期"] = int(datetime.now().timestamp() * 1000)
    if article_type:
        fields["选题类型"] = article_type
    if words:
        fields["预估字数"] = words
    if cover:
        fields["封面类型"] = cover
    if keywords:
        fields["标题关键词"] = keywords
    if status:
        fields["状态"] = status
    fields["阅读量"] = reads
    fields["推荐率"] = 0
    fields["完读率"] = 0
    if geo:
        fields["GEO评分"] = geo
    if layout:
        fields["排版"] = layout
    if note:
        fields["备注"] = note

    result = _api("POST", f"/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records",
                  body={"fields": fields}, token=token)
    if result.get("code") == 0:
        rid = result["data"]["record"]["record_id"]
        _log(f"✅ 记录已写入: record_id={rid}")
        return rid
    else:
        _log(f"❌ 写入失败: {result.get('msg')}")
        return None


def list_records(limit=10):
    """列出最近记录"""
    token = get_token()
    table_id = get_table_id(token)
    result = _api("GET", f"/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records?page_size={limit}", token=token)
    if result.get("code") != 0:
        _log(f"❌ 查询失败: {result.get('msg')}")
        return
    items = result.get("data", {}).get("items", [])
    if not items:
        _log("暂无记录")
        return
    _log(f"\n{'='*60}")
    _log(f"  最近 {len(items)} 条文章记录")
    _log(f"{'='*60}")
    for i, item in enumerate(items, 1):
        f = item.get("fields", {})
        rid = item.get("record_id", "?")
        title = f.get("标题", "?")
        status = f.get("状态", "?")
        atype = f.get("选题类型", "-")
        reads = f.get("阅读量", 0)
        rec_rate = f.get("推荐率", 0)
        geo = f.get("GEO评分", 0)
        _log(f"\n  {i}. {title}")
        _log(f"     类型:{atype} | 状态:{status} | 阅读:{reads} | 推荐:{rec_rate}% | GEO:{geo}")
        _log(f"     id:{rid}")


def update_record(record_id, reads=None, recommend=None, finish=None, status=None, note=None, layout=None):
    """更新已有记录的阅读数据"""
    token = get_token()
    table_id = get_table_id(token)
    fields = {}
    if reads is not None:
        fields["阅读量"] = reads
    if recommend is not None:
        fields["推荐率"] = recommend
    if finish is not None:
        fields["完读率"] = finish
    if status:
        fields["状态"] = status
    if layout:
        fields["排版"] = layout
    if note:
        fields["备注"] = note
    if not fields:
        _log("没有指定更新字段")
        return
    result = _api("PUT",
                  f"/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records/{record_id}",
                  body={"fields": fields}, token=token)
    if result.get("code") == 0:
        _log(f"✅ 更新成功: record_id={record_id}")
    else:
        _log(f"❌ 更新失败: {result.get('msg')}")


def main():
    parser = argparse.ArgumentParser(description="飞书多维表格 - 公众号文章指标追踪")
    sub = parser.add_subparsers(dest="cmd")

    # add
    p_add = sub.add_parser("add", help="写入新文章记录")
    p_add.add_argument("--title", "-t", required=True, help="文章标题")
    p_add.add_argument("--type", "-T", default="", help="选题类型: 热点解读/工具教程/行业分析")
    p_add.add_argument("--words", "-w", type=int, default=0, help="预估字数")
    p_add.add_argument("--cover", "-c", default="", help="封面类型: AI生成/手动/截图")
    p_add.add_argument("--keywords", "-k", default="", help="标题关键词(逗号分隔)")
    p_add.add_argument("--status", "-s", default="草稿", help="状态: 草稿/已发布")
    p_add.add_argument("--geo", "-g", type=int, default=0, help="GEO评分(1-10)")
    p_add.add_argument("--note", "-n", default="", help="备注")
    p_add.add_argument("--date", "-d", default="", help="发布日期 YYYY-MM-DD")
    p_add.add_argument("--reads", type=int, default=0, help="阅读量")
    p_add.add_argument("--layout", "-L", default="", help="排版方式: wenyan/direct/手动")

    # list
    p_list = sub.add_parser("list", help="查看最近记录")
    p_list.add_argument("--limit", "-l", type=int, default=10, help="显示条数")

    # update
    p_upd = sub.add_parser("update", help="更新阅读数据")
    p_upd.add_argument("--record-id", "-r", required=True, help="记录ID")
    p_upd.add_argument("--reads", type=int, help="阅读量")
    p_upd.add_argument("--recommend", type=int, help="推荐率(百分比)")
    p_upd.add_argument("--finish", type=int, help="完读率(百分比)")
    p_upd.add_argument("--status", default="", help="状态")
    p_upd.add_argument("--layout", "-L", default="", help="排版方式: wenyan/direct/手动")
    p_upd.add_argument("--note", default="", help="备注")

    args = parser.parse_args()

    if args.cmd == "add":
        add_record(args.title, args.type, args.words, args.cover,
                   args.keywords, args.status, args.geo, args.note, args.date, args.layout, args.reads)
    elif args.cmd == "list":
        list_records(args.limit)
    elif args.cmd == "update":
        update_record(args.record_id, args.reads, args.recommend,
                      args.finish, args.status, args.note, args.layout)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
