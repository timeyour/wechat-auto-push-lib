"""
记忆引擎 - journal.jsonl 写入与查询
每篇文章的执行轨迹、风格参数、效果数据统一记录。

用法：
    from memory_engine import journal

    # 发布成功后写入轨迹
    journal.record_article(article)

    # 手动补充效果数据（阅读量等）
    journal.update_outcome(slug, reads=1234, likes=56)

    # 查询某主题的历史效果
    journal.query_by_theme("pie")

    # 获取最佳标题风格
    journal.top_titles(n=5)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DATA_DIR

JOURNAL_FILE = DATA_DIR / "journal.jsonl"
JOURNAL_FILE.parent.mkdir(exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_file():
    if not JOURNAL_FILE.exists():
        JOURNAL_FILE.write_text("", encoding="utf-8")


# ── 写入 ──────────────────────────────────────────────────────────────────────


def record_article(
    slug: str,
    title: str,
    source: str = "manual",
    theme_id: str = "pie",
    style_profile: Optional[Dict[str, str]] = None,
    author: str = "",
    words: int = 0,
    draft_id: Optional[str] = None,
    published_url: Optional[str] = None,
    publish_time: Optional[str] = None,
    skill_signals: Optional[List[Dict[str, Any]]] = None,
    phase_trace: Optional[List[Dict[str, Any]]] = None,
    tags: Optional[List[str]] = None,
    notes: str = "",
) -> str:
    """
    记录一篇文章的完整执行轨迹。

    Returns: slug
    """
    _ensure_file()

    # 防止重复写入
    existing = get_by_slug(slug)
    if existing:
        print(f"[journal] {slug} 已存在，跳过写入")
        return slug

    entry = {
        "slug": slug,
        "title": title,
        "source": source,             # "manual" | "rss" | "sop"
        "theme_id": theme_id,
        "style_profile": style_profile or {},
        "author": author,
        "words": words,
        "tags": tags or [],
        "notes": notes,
        # 执行轨迹
        "skill_signals": skill_signals or [],  # [{skill, version, success, duration_ms, error}]
        "phase_trace": phase_trace or [],      # [{phase, status, output_path}]
        # 发布记录
        "draft_id": draft_id,
        "published_url": published_url,
        "publish_time": publish_time or _now(),
        "recorded_at": _now(),
        # 效果数据（后续手动补充）
        "outcome": {
            "reads": None,
            "likes": None,
            "shares": None,
            "comments": None,
            "updated_at": None,
        },
    }

    with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[journal] 记录: {slug} — {title}")
    return slug


def update_outcome(
    slug: str,
    reads: Optional[int] = None,
    likes: Optional[int] = None,
    shares: Optional[int] = None,
    comments: Optional[int] = None,
    notes: str = "",
) -> bool:
    """手动补充效果数据。"""
    _ensure_file()
    entries = _load_all()
    updated = False

    for entry in entries:
        if entry.get("slug") == slug:
            if reads is not None:
                entry["outcome"]["reads"] = reads
            if likes is not None:
                entry["outcome"]["likes"] = likes
            if shares is not None:
                entry["outcome"]["shares"] = shares
            if comments is not None:
                entry["outcome"]["comments"] = comments
            if notes:
                entry["notes"] = (entry.get("notes") or "") + f"\n[{_now()}] {notes}"
            entry["outcome"]["updated_at"] = _now()
            updated = True

    if updated:
        _save_all(entries)
        print(f"[journal] 更新效果: {slug}")
    else:
        print(f"[journal] 未找到: {slug}")

    return updated


# ── 查询 ──────────────────────────────────────────────────────────────────────


def _load_all() -> List[Dict[str, Any]]:
    _ensure_file()
    entries = []
    with open(JOURNAL_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def _save_all(entries: List[Dict[str, Any]]):
    with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def get_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """按 slug 查单条。"""
    for entry in _load_all():
        if entry.get("slug") == slug:
            return entry
    return None


def query_by_theme(theme_id: str) -> List[Dict[str, Any]]:
    """查某主题的全部文章。"""
    return [e for e in _load_all() if e.get("theme_id") == theme_id]


def query_by_tag(tag: str) -> List[Dict[str, Any]]:
    """按标签查询。"""
    return [e for e in _load_all() if tag in (e.get("tags") or [])]


def query_by_source(source: str) -> List[Dict[str, Any]]:
    """按来源查询（manual / rss / sop）。"""
    return [e for e in _load_all() if e.get("source") == source]


def top_titles(n: int = 5) -> List[Dict[str, Any]]:
    """
    效果最好的 n 篇文章。
    按 reads > likes > shares 综合排序。
    """
    entries = [e for e in _load_all()
               if e.get("outcome", {}).get("reads") is not None]
    def score(e):
        o = e.get("outcome", {})
        return (o.get("reads") or 0) * 1 + (o.get("likes") or 0) * 10 + (o.get("shares") or 0) * 5
    entries.sort(key=score, reverse=True)
    return entries[:n]


def worst_titles(n: int = 5) -> List[Dict[str, Any]]:
    """效果最差的 n 篇（阅读量已知但偏低）。"""
    entries = [e for e in _load_all()
               if e.get("outcome", {}).get("reads") is not None]
    def score(e):
        return e.get("outcome", {}).get("reads") or 0
    entries.sort(key=score)
    return entries[:n]


def skill_stats() -> Dict[str, Any]:
    """
    各 skill 的成功率统计。
    用于识别哪些 skill 经常出问题。
    """
    all_signals: Dict[str, dict] = {}
    for entry in _load_all():
        for sig in entry.get("skill_signals") or []:
            skill = sig.get("skill", "unknown")
            if skill not in all_signals:
                all_signals[skill] = {"total": 0, "success": 0, "errors": []}
            s = all_signals[skill]
            s["total"] += 1
            if sig.get("success"):
                s["success"] += 1
            else:
                err = sig.get("error", "")
                if err:
                    s["errors"].append(err[:100])

    return {
        skill: {
            "total": v["total"],
            "success_rate": round(v["success"] / v["total"] * 100, 1) if v["total"] else 0,
            "error_samples": list(dict.fromkeys(v["errors"]))[:3],
        }
        for skill, v in sorted(all_signals.items())
    }


def theme_stats() -> Dict[str, Any]:
    """
    各主题的效果统计。
    用于识别哪种风格更适合哪类内容。
    """
    from collections import defaultdict
    stats: Dict[str, dict] = defaultdict(lambda: {"count": 0, "total_reads": 0, "total_likes": 0})

    for entry in _load_all():
        theme = entry.get("theme_id", "unknown")
        outcome = entry.get("outcome", {})
        reads = outcome.get("reads") or 0
        likes = outcome.get("likes") or 0

        if outcome.get("reads") is not None:
            stats[theme]["count"] += 1
            stats[theme]["total_reads"] += reads
            stats[theme]["total_likes"] += likes

    return {
        theme: {
            "articles": v["count"],
            "avg_reads": round(v["total_reads"] / v["count"]) if v["count"] else 0,
            "avg_likes": round(v["total_likes"] / v["count"], 1) if v["count"] else 0,
        }
        for theme, v in sorted(stats.items(), key=lambda x: x[1]["avg_reads"], reverse=True)
    }


def tag_stats() -> Dict[str, Any]:
    """
    各标签的平均阅读量。
    用于识别哪些话题类型效果更好。
    """
    from collections import defaultdict
    tag_data: Dict[str, dict] = defaultdict(lambda: {"count": 0, "total_reads": 0})

    for entry in _load_all():
        outcome = entry.get("outcome", {})
        if outcome.get("reads") is None:
            continue
        for tag in entry.get("tags") or []:
            tag_data[tag]["count"] += 1
            tag_data[tag]["total_reads"] += outcome.get("reads", 0) or 0

    return {
        tag: {
            "articles": v["count"],
            "avg_reads": round(v["total_reads"] / v["count"]) if v["count"] else 0,
        }
        for tag, v in sorted(tag_data.items(), key=lambda x: x[1]["avg_reads"], reverse=True)
    }


def export_csv(path: Optional[Path] = None) -> Path:
    """导出 CSV，用于外部分析。"""
    import csv
    out_path = path or (DATA_DIR / "journal_export.csv")
    entries = _load_all()

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "slug", "title", "source", "theme_id", "author", "words",
            "tags", "publish_time",
            "reads", "likes", "shares", "comments", "notes",
        ])
        writer.writeheader()
        for e in entries:
            o = e.get("outcome", {})
            writer.writerow({
                "slug": e.get("slug", ""),
                "title": e.get("title", ""),
                "source": e.get("source", ""),
                "theme_id": e.get("theme_id", ""),
                "author": e.get("author", ""),
                "words": e.get("words", 0),
                "tags": "|".join(e.get("tags") or []),
                "publish_time": e.get("publish_time", ""),
                "reads": o.get("reads", ""),
                "likes": o.get("likes", ""),
                "shares": o.get("shares", ""),
                "comments": o.get("comments", ""),
                "notes": e.get("notes", ""),
            })

    print(f"[journal] 导出: {out_path}")
    return out_path


def summary() -> Dict[str, Any]:
    """全量统计摘要。"""
    entries = _load_all()
    with_outcome = [e for e in entries if e.get("outcome", {}).get("reads") is not None]
    return {
        "total_articles": len(entries),
        "with_outcome": len(with_outcome),
        "by_source": _counts(entries, "source"),
        "by_theme": _counts(entries, "theme_id"),
        "theme_stats": theme_stats(),
        "tag_stats": tag_stats(),
        "skill_stats": skill_stats(),
        "top_titles": [
            {"slug": e["slug"], "title": e["title"],
             "reads": e["outcome"].get("reads")}
            for e in top_titles(3)
        ],
    }


def _counts(entries: List[Dict], key: str) -> Dict[str, int]:
    from collections import Counter
    return dict(Counter(e.get(key, "unknown") for e in entries))


# ── CLI ───────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"

    if cmd == "summary":
        import pprint
        pprint.pprint(summary())
    elif cmd == "skills":
        import pprint
        pprint.pprint(skill_stats())
    elif cmd == "themes":
        import pprint
        pprint.pprint(theme_stats())
    elif cmd == "export":
        export_csv()
    elif cmd == "top":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        import pprint
        pprint.pprint(top_titles(n))
    else:
        print(f"用法: python memory_engine.py [summary|skills|themes|export|top]")
