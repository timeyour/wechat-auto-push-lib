#!/usr/bin/env python3
"""
fetch_github_trending.py
抓取 GitHub Trending（通过 GitHub Search API），输出 AI/开发者相关的 repo 到 JSON
用法:
  python fetch_github_trending.py          # 最近7天（按stars排序）
  python fetch_github_trending.py <语言>   # 指定语言，如 python / javascript
"""

import sys
import json
import re
import datetime
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
OUT_FILE = BASE_DIR / "data" / "github_trending.json"
OUT_FILE.parent.mkdir(exist_ok=True)

FETCH_TIMEOUT = 20

# Load API key from config
CONFIG_FILE = BASE_DIR.parent / "config.json"


def load_api_key() -> str:
    try:
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return config.get("github_token", "") or os.getenv("GITHUB_TOKEN", "")
    except Exception:
        return os.getenv("GITHUB_TOKEN", "")


def fetch_github_api(url: str) -> dict | None:
    """Fetch JSON from GitHub API."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CorpusPlaybook/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    api_key = load_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        import requests
        r = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 403:
            print(f"GitHub API rate limit hit (403). Add GITHUB_TOKEN to config.json")
            return None
        else:
            print(f"GitHub API error: {r.status_code} {r.text[:200]}")
            return None
    except Exception as e:
        print(f"Request error: {e}")
        return None


def fetch_trending_repos(language: str = "all") -> list[dict]:
    """
    Fetch trending repos using GitHub Search API.
    Searches for repos created/pushed recently with most stars.
    """
    # Calculate date range: repos created or pushed in last 7 days
    date_7d = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

    # Build search query: active repos with most stars in last week
    queries = [
        # High-star recent repos
        f"created:>{date_7d}+stars:>100+pushed:>{date_7d}",
        # AI/Agent related specifically (broader window)
        f"AI+OR+agent+OR+llm+OR+gpt+OR+claude+created:>2025-01-01+stars:>500+pushed:>{date_7d}",
    ]

    all_repos = {}

    for query in queries:
        lang_param = f"+language:{language}" if language != "all" else ""
        url = f"https://api.github.com/search/repositories?q={query}{lang_param}&sort=stars&order=desc&per_page=30"

        print(f"  Query: {query[:80]}")
        data = fetch_github_api(url)

        if not data or "items" not in data:
            continue

        for item in data.get("items", []):
            key = item["full_name"]
            if key not in all_repos:
                all_repos[key] = {
                    "name": item.get("name", ""),
                    "full_name": item.get("full_name", ""),
                    "path": "/" + item.get("full_name", ""),
                    "description": item.get("description", "") or "",
                    "language": item.get("language", "") or "",
                    "stars": item.get("stargazers_count", 0),
                    "forks": item.get("forks_count", 0),
                    "topics": item.get("topics", []),
                    "url": item.get("html_url", ""),
                    "pushed_at": item.get("pushed_at", ""),
                    "created_at": item.get("created_at", ""),
                }

    return list(all_repos.values())


def fetch_trending_by_language(language: str) -> list[dict]:
    """Fetch repos for a specific language."""
    date_7d = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    url = (
        f"https://api.github.com/search/repositories"
        f"?q=pushed:>{date_7d}+stars:>100+language:{language}"
        f"&sort=stars&order=desc&per_page=20"
    )
    data = fetch_github_api(url)
    if not data:
        return []
    return [
        {
            "name": item.get("name", ""),
            "full_name": item.get("full_name", ""),
            "path": "/" + item.get("full_name", ""),
            "description": item.get("description", "") or "",
            "language": item.get("language", "") or "",
            "stars": item.get("stargazers_count", 0),
            "forks": item.get("forks_count", 0),
            "topics": item.get("topics", [])[:5],
            "url": item.get("html_url", ""),
            "pushed_at": item.get("pushed_at", ""),
        }
        for item in data.get("items", [])
    ]


# AI-relevant keywords for filtering
AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "agent", "rag", "openai", "ollama",
    "model", "embedding", "vector", "chatbot", "assistant", "langchain",
    "agent", "autogen", "crewai", "n8n", "automation", "workflow",
    "copilot", "cursor", "windsurf", "devin", "swe-agent", "tool-use",
    "image", "video", "generation", "stable-diffusion", "midjourney",
    "tts", "voice", "ocr", "speech", "translation", "rag",
]


def is_ai_related(repo: dict) -> bool:
    text = (
        repo["name"].lower()
        + " " + repo["description"].lower()
        + " " + " ".join(repo.get("topics", []))
    )
    return any(kw in text for kw in AI_KEYWORDS)


def main():
    import sys as _sys
    try:
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    language = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"Fetching GitHub Trending: language={language}")

    if language == "all":
        repos = fetch_trending_repos()
    else:
        repos = fetch_trending_by_language(language)

    if not repos:
        print("WARNING: No repos fetched, generating demo data.")
        repos = generate_demo()

    # Filter AI-related
    ai_repos = [r for r in repos if is_ai_related(r)]
    ai_repos.sort(key=lambda x: x["stars"], reverse=True)

    # All lang repos sorted
    repos.sort(key=lambda x: x["stars"], reverse=True)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    result = {
        "period": "7天内",
        "fetched_at": now_str,
        "url": "https://api.github.com/search/repositories",
        "total_repos": len(repos),
        "ai_related_count": len(ai_repos),
        "repos": repos[:20],
        "ai_repos": ai_repos[:15],
        "has_api_key": bool(load_api_key()),
    }

    OUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    size = OUT_FILE.stat().st_size
    print(f"DONE: {OUT_FILE} ({size // 1024}KB)")
    print(f"  Total: {len(repos)} | AI-related: {len(ai_repos)}")
    for r in ai_repos[:5]:
        try:
            desc = r["description"][:80]
        except Exception:
            desc = ""
        print(f"  [{r['language'] or '?'}] {r['name']} ({r['stars']:,} stars)")
        if desc:
            print(f"    {desc}")


def generate_demo() -> list[dict]:
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    return [
        {
            "name": "SWE-agent",
            "full_name": "princeton-nlp/SWE-agent",
            "path": "/princeton-nlp/SWE-agent",
            "description": "Agent for automating software engineering tasks",
            "language": "Python",
            "stars": 12400,
            "forks": 890,
            "topics": ["ai", "agent", "software-engineering", "llm"],
            "url": "https://github.com/princeton-nlp/SWE-agent",
            "pushed_at": now,
        },
        {
            "name": "AgentSeek",
            "full_name": "agentseek/AgentSeek",
            "path": "/agentseek/AgentSeek",
            "description": "Open source autonomous AI agents platform",
            "language": "TypeScript",
            "stars": 8200,
            "forks": 620,
            "topics": ["ai", "agent", "autonomous", "open-source"],
            "url": "https://github.com/agentseek/AgentSeek",
            "pushed_at": now,
        },
        {
            "name": "Dify",
            "full_name": "langgenius/dify",
            "path": "/langgenius/dify",
            "description": "Create AI workflows, chatbots, and agents",
            "language": "TypeScript",
            "stars": 28500,
            "forks": 4200,
            "topics": ["llm-app", "ai-agent", "workflow", "rag"],
            "url": "https://github.com/langgenius/dify",
            "pushed_at": now,
        },
    ]


if __name__ == "__main__":
    main()
