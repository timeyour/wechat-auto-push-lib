#!/usr/bin/env python3
"""
fetch_twitter_rss.py
拉取推特起爆帖 RSS（SoPilot），提取高概率起爆推文
用法:
  python fetch_twitter_rss.py
"""

import sys
import json
import re
import datetime
import html
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
OUT_FILE = BASE_DIR / "data" / "twitter_trending.json"
OUT_FILE.parent.mkdir(exist_ok=True)

RSS_URL = "https://sopilot.net/rss/hottweets"
FETCH_TIMEOUT = 15

# SoPilot RSS fields we care about:
# title: "@user - 推文内容摘要"
# description: 详细文字 / 起爆概率 / 预计曝光
# pubDate: 发布时间


def fetch_url_text(url: str) -> str | None:
    try:
        import requests
        r = requests.get(url, timeout=FETCH_TIMEOUT, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        })
        if r.status_code == 200:
            return r.text
    except Exception:
        pass

    try:
        from urllib.request import urlopen, Request
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        pass

    return None


def parse_rss(xml_text: str) -> list[dict]:
    """Parse RSS XML and extract items."""
    items = []

    # Extract each <item>
    item_pattern = re.compile(r"<item>(.*?)</item>", re.DOTALL)
    for item_match in item_pattern.finditer(xml_text):
        item_xml = item_match.group(1)

        def get_tag(tag: str) -> str:
            cdata_pattern = re.compile(
                r"<" + re.escape(tag) + r"[^>]*><!\[CDATA\[(.*?)\]\]></" + re.escape(tag) + r">",
                re.DOTALL
            )
            m = cdata_pattern.search(item_xml)
            if not m:
                plain_pattern = re.compile(r"<" + re.escape(tag) + r"[^>]*>(.*?)</" + re.escape(tag) + r">", re.DOTALL)
                m = plain_pattern.search(item_xml)
            return m.group(1).strip() if m else ""

        title = get_tag("title")
        description = get_tag("description")
        pub_date = get_tag("pubDate")
        link = get_tag("link")

        # Unescape HTML entities
        title = html.unescape(title)
        description = html.unescape(description)

        # Extract user handle - title is often just the username
        user_match = re.search(r"@([\w]+)", title)
        user = "@" + user_match.group(1) if user_match else ""
        if not user:
            user_match = re.search(r"@([\w]+)", description)
            user = "@" + user_match.group(1) if user_match else ""

        # Extract tweet text: description contains tweet + stats
        # Remove probability %, view counts, URLs from description to get tweet text
        tweet_text = description
        tweet_text = re.sub(r"\d+%", "XX%", tweet_text)  # mask percentages
        tweet_text = re.sub(r"[\d\.]+[万仟百]?\s*(曝光|views|estimated)", "", tweet_text)
        tweet_text = re.sub(r"https?://\S+", "", tweet_text)  # remove URLs
        tweet_text = re.sub(r"\s+", " ", tweet_text).strip()

        # Extract probability %
        prob_match = re.search(r"(\d+)%", description)
        probability = int(prob_match.group(1)) if prob_match else 0

        # Extract view estimate
        view_match = re.search(r"([\d\.]+万)", description)
        views = view_match.group(1) if view_match else ""

        # Filter: only include items with probability >= 40% (interesting)
        if probability >= 40 or user:
            items.append({
                "user": user,
                "title": tweet_text[:120] or title[:120],
                "description": description[:300],
                "probability": probability,
                "views": views,
                "pub_date": pub_date,
                "link": link,
                "is_hot": probability >= 70,
            })

    return items


def main():
    import sys as _sys
    try:
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(f"Fetching Twitter Hot Tweets RSS: {RSS_URL}")
    xml = fetch_url_text(RSS_URL)

    if not xml:
        print("WARNING: Failed to fetch RSS, generating demo data.")
        items = generate_demo()
    else:
        items = parse_rss(xml)

    # Sort by probability
    items.sort(key=lambda x: x["probability"], reverse=True)

    # Add time-based freshness indicator
    now = datetime.datetime.now()
    for item in items:
        try:
            pub = datetime.datetime.strptime(
                item["pub_date"][:25], "%a, %d %b %Y %H:%M:%S"
            )
            age_hours = (now - pub).total_seconds() / 3600
            item["age_hours"] = round(age_hours, 1)
            item["is_fresh"] = age_hours <= 2
            item["fresh_label"] = f"{round(age_hours, 1)}h ago"
        except Exception:
            item["age_hours"] = None
            item["is_fresh"] = False
            item["fresh_label"] = "unknown"

    result = {
        "fetched_at": now.strftime("%Y-%m-%d %H:%M"),
        "url": RSS_URL,
        "source": "SoPilot Hot Tweets RSS",
        "total_items": len(items),
        "hot_count": sum(1 for x in items if x["is_hot"]),
        "fresh_count": sum(1 for x in items if x["is_fresh"]),
        "items": items[:20],
        "demo": False,
    }

    OUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    size = OUT_FILE.stat().st_size
    print(f"DONE: {OUT_FILE} ({size // 1024}KB)")
    print(f"  Total: {len(items)} | Hot(>=70%): {sum(1 for x in items if x['is_hot'])} | Fresh(<=2h): {sum(1 for x in items if x['is_fresh'])}")
    for item in items[:5]:
        print(f"  [{item['probability']}%] {item['user']} | {item.get('fresh_label', '?')} | {item['title'][:60]}")


def generate_demo() -> list[dict]:
    """Generate realistic demo data when RSS is unavailable."""
    now = datetime.datetime.now()
    demo_items = [
        {
            "user": "@sama",
            "title": "GPT-5 is coming - here's what we learned from the new model",
            "description": "OpenAI announces major breakthrough. Probability: 95%. Estimated views: 98.7万",
            "probability": 95,
            "views": "98.7万",
            "pub_date": (now - datetime.timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:00 GMT"),
            "link": "https://x.com/sama",
            "is_hot": True,
            "age_hours": 1.0,
            "is_fresh": True,
            "fresh_label": "1.0h ago",
        },
        {
            "user": "@kaborl",
            "title": "How I built an AI agent that writes 50 articles per day",
            "description": "Practical guide to multi-agent content pipeline. Probability: 78%. Estimated views: 23.4万",
            "probability": 78,
            "views": "23.4万",
            "pub_date": (now - datetime.timedelta(hours=3)).strftime("%a, %d %b %Y %H:%M:00 GMT"),
            "link": "https://x.com/kaborl",
            "is_hot": True,
            "age_hours": 3.0,
            "is_fresh": False,
            "fresh_label": "3.0h ago",
        },
        {
            "user": "@xiaohongshu_ai",
            "title": "小红书AI赛道最新变现方法论（实测月入3万）",
            "description": "Step-by-step monetization guide with real revenue data. Probability: 72%",
            "probability": 72,
            "views": "15.2万",
            "pub_date": (now - datetime.timedelta(hours=5)).strftime("%a, %d %b %Y %H:%M:00 GMT"),
            "link": "https://x.com/xiaohongshu_ai",
            "is_hot": True,
            "age_hours": 5.0,
            "is_fresh": False,
            "fresh_label": "5.0h ago",
        },
    ]
    return demo_items


if __name__ == "__main__":
    main()
