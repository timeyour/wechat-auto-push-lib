#!/usr/bin/env python3
"""
fetch_all.py
一键抓取所有热榜数据到 JSON
用法:
  python fetch_all.py           # 抓全部
  python fetch_all.py github    # 只抓 GitHub
  python fetch_all.py twitter    # 只抓 Twitter
"""

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
PY = os.environ.get("PYTHON", sys.executable)


def run(name: str, script: str) -> bool:
    print(f"\n{'='*50}")
    print(f"  {name}")
    print('='*50)
    result = subprocess.run(
        [PY, str(BASE_DIR / script)],
        capture_output=False,
        cwd=str(BASE_DIR),
    )
    ok = result.returncode == 0
    print(f"  -> {'OK' if ok else 'FAILED'}")
    return ok


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["github", "twitter"]
    results = {}

    if "github" in targets:
        results["github"] = run("GitHub Trending (AI repos)", "fetch_github_trending.py")

    if "twitter" in targets:
        results["twitter"] = run("Twitter Hot Tweets (SoPilot RSS)", "fetch_twitter_rss.py")

    print(f"\n{'='*50}")
    print("  Summary")
    print('='*50)
    for name, ok in results.items():
        data_file = BASE_DIR / "data" / f"{name}_trending.json"
        size = data_file.stat().st_size // 1024 if data_file.exists() else 0
        status = "OK" if ok else "FAILED"
        print(f"  {name}: {status} | {size}KB")

    # Generate hot topics for monitor
    generate_hot_topics()


def generate_hot_topics():
    """Derive 3-5 hot topic suggestions from fetched data."""
    import json

    topics = []
    data_dir = BASE_DIR / "data"

    # From GitHub
    gh_file = data_dir / "github_trending.json"
    if gh_file.exists():
        try:
            gh = json.loads(gh_file.read_text(encoding="utf-8"))
            for repo in gh.get("ai_repos", [])[:3]:
                topics.append({
                    "type": "github",
                    "title": repo["name"],
                    "desc": repo.get("description", "")[:80],
                    "stars": repo["stars"],
                    "url": repo["url"],
                    "topic_id": None,  # to be matched
                })
        except Exception:
            pass

    # From Twitter
    tw_file = data_dir / "twitter_trending.json"
    if tw_file.exists():
        try:
            tw = json.loads(tw_file.read_text(encoding="utf-8"))
            for item in tw.get("items", [])[:3]:
                topics.append({
                    "type": "twitter",
                    "title": item.get("title", "")[:60] or item["user"],
                    "user": item["user"],
                    "probability": item["probability"],
                    "url": item["link"],
                    "topic_id": None,
                })
        except Exception:
            pass

    # Save hot topics
    hot_file = data_dir / "hot_topics.json"
    hot_file.write_text(
        json.dumps({
            "generated_at": subprocess.run(
                [PY, "-c", "from datetime import datetime; print(datetime.now().strftime('%Y-%m-%d %H:%M'))"],
                capture_output=True, text=True,
            ).stdout.strip(),
            "topics": topics,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  hot_topics: {len(topics)} items -> {hot_file.name}")


if __name__ == "__main__":
    main()
