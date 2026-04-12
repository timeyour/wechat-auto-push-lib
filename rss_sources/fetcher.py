"""
RSS 多源抓取模块
支持 RSS 摘要 + 原文全文两种模式，自动去重。
"""
from __future__ import annotations

import feedparser
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from readability import Document

from config import RSS_SOURCES, MAX_ARTICLES_PER_SOURCE, DATA_DIR

logger = logging.getLogger(__name__)

PUBLISHED_FILE = DATA_DIR / "published_urls.json"


def _load_published_urls() -> set:
    if PUBLISHED_FILE.exists():
        try:
            data = json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))
            return set(data.get("urls", []))
        except (json.JSONDecodeError, KeyError):
            pass
    return set()


def _save_published_urls(urls: set):
    PUBLISHED_FILE.write_text(
        json.dumps({"urls": sorted(urls), "updated_at": datetime.now().isoformat()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _url_fingerprint(url: str) -> str:
    """URL 指纹（去除查询参数用于去重）"""
    return hashlib.md5(url.split("?")[0].split("#")[0].rstrip("/").encode()).hexdigest()


@dataclass
class Article:
    """抓取到的文章对象"""
    title: str
    link: str
    summary: str
    content: str
    author: str = ""
    source_name: str = ""
    tag: str = ""
    published: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cover_url: str = ""
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        """初始化后处理"""
        # 去除首尾空白
        self.title = self.title.strip()
        self.link = self.link.strip()
        self.summary = self.summary.strip()
        self.content = self.content.strip()
        self.author = self.author.strip()
        # 生成指纹
        self.fingerprint = _url_fingerprint(self.link)

    def __repr__(self) -> str:
        return f"Article({self.title!r}, from={self.source_name!r})"


def _extract_cover_url(entry) -> str:
    """从 RSS entry 中提取封面图 URL"""
    for key in ("media_thumbnail", "media_content"):
        if hasattr(entry, key):
            media = getattr(entry, key)
            if media:
                return media[0].get("url", "")
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/"):
                return enc.get("href", "")
    html = entry.get("summary", "") or entry.get("content", "") or ""
    if html:
        img = BeautifulSoup(html, "lxml").find("img")
        if img:
            return img.get("src", "")
    return ""


def _is_chinese_content(text: str, threshold: float = 0.3) -> bool:
    if not text:
        return False
    chinese = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return chinese / max(len(text), 1) >= threshold


def _fetch_full_content(url: str, source_name: str = "") -> str:
    """使用 readability 算法提取正文全文"""
    try:
        resp = requests.get(
            url, timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9",
            },
        )
        resp.raise_for_status()
        if resp.encoding and resp.encoding.lower() not in ("utf-8", "utf8"):
            resp.encoding = "utf-8"
        doc = Document(resp.text)
        soup = BeautifulSoup(doc.summary(), "lxml")
        for tag in soup.find_all(["script", "style", "iframe", "noscript"]):
            tag.decompose()
        text_len = len(soup.get_text(strip=True))
        if text_len < 100:
            logger.warning(f"[{source_name}] 正文过短 ({text_len}字): {url[:50]}")
            return ""
        logger.info(f"[{source_name}] 原文抓取成功 ({text_len}字)")
        return str(soup)
    except Exception as e:
        logger.error(f"[{source_name}] 原文抓取失败: {url[:50]} -> {e}")
        return ""


def fetch_rss_feed(source: dict) -> list[Article]:
    """抓取单个 RSS 源，返回 Article 列表"""
    name, url, tag = source["name"], source["url"], source.get("tag", "")
    logger.info(f"抓取 RSS 源: {name}")

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        logger.error(f"RSS 解析失败 [{name}]: {e}")
        return []

    if feed.bozo and not feed.entries:
        logger.error(f"RSS 源异常 [{name}]")
        return []

    published_urls = _load_published_urls()
    articles = []

    for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE * 2]:
        link = entry.get("link", "")
        if not link:
            continue
        fp = _url_fingerprint(link)
        if fp in published_urls:
            continue

        title = entry.get("title", "无标题")
        summary = entry.get("summary", "") or ""

        # 获取正文内容
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        if not content:
            content = summary

        # 内容太短则抓全文
        body_text = BeautifulSoup(content, "lxml").get_text(strip=True)
        if len(body_text) < 300 and link:
            full = _fetch_full_content(link, name)
            if full and len(BeautifulSoup(full, "lxml").get_text(strip=True)) > 100:
                content = full

        if len(BeautifulSoup(content, "lxml").get_text(strip=True)) < 100:
            continue

        # 中文过滤
        combined = title + " " + body_text[:500]
        if not _is_chinese_content(combined, 0.3):
            continue

        # 作者
        author = ""
        if hasattr(entry, "author"):
            author = entry.author
        elif hasattr(entry, "authors") and entry.authors:
            author = entry.authors[0].get("name", "")

        # 发布时间
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                from email.utils import parsedate_to_datetime
                published = parsedate_to_datetime(entry.published_parsed)
            except Exception:
                pass

        # 封面图
        cover_url = _extract_cover_url(entry)
        if not cover_url and content:
            img = BeautifulSoup(content, "lxml").find("img")
            if img:
                cover_url = img.get("src", "")

        articles.append(Article(
            title=title, link=link, summary=summary, content=content,
            author=author, source_name=name, tag=tag,
            published=published, cover_url=cover_url,
        ))
        published_urls.add(fp)

        if len(articles) >= MAX_ARTICLES_PER_SOURCE:
            break

    logger.info(f"[{name}] 抓取到 {len(articles)} 篇新文章")
    return articles


def fetch_all_sources() -> list[Article]:
    """抓取所有配置的 RSS 源"""
    all_articles = []
    for source in RSS_SOURCES:
        try:
            all_articles.extend(fetch_rss_feed(source))
        except Exception as e:
            logger.error(f"抓取失败 [{source['name']}]: {e}")
    logger.info(f"共抓取 {len(all_articles)} 篇新文章")
    return all_articles


def mark_as_published(article: Article):
    """将文章标记为已发布"""
    urls = _load_published_urls()
    urls.add(article.fingerprint)
    _save_published_urls(urls)


def mark_batch_as_published(articles: list[Article]):
    """批量标记为已发布"""
    urls = _load_published_urls()
    for a in articles:
        urls.add(a.fingerprint)
    _save_published_urls(urls)
    logger.info(f"已批量标记 {len(articles)} 篇")
