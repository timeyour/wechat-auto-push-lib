"""
rss_sources 模块单元测试
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from rss_sources.fetcher import (
    Article,
    _url_fingerprint,
    _is_chinese_content,
    fetch_rss_feed,
)


class TestUrlFingerprint:
    """URL 指纹测试"""

    def test_basic_fingerprint(self):
        """基本指纹生成"""
        url = "https://example.com/article"
        fp = _url_fingerprint(url)
        assert len(fp) == 32  # MD5 长度
        assert fp.isalnum()

    def test_same_fingerprint_different_params(self):
        """去除查询参数"""
        url1 = "https://example.com/article?id=1"
        url2 = "https://example.com/article?id=2"
        assert _url_fingerprint(url1) == _url_fingerprint(url2)

    def test_trailing_slash(self):
        """去除尾部斜杠"""
        url1 = "https://example.com/article/"
        url2 = "https://example.com/article"
        assert _url_fingerprint(url1) == _url_fingerprint(url2)


class TestIsChineseContent:
    """中文内容检测测试"""

    def test_pure_chinese(self):
        """纯中文内容"""
        assert _is_chinese_content("这是一段中文内容") is True

    def test_mixed_content(self):
        """中英混合"""
        # 中文超过30%阈值
        assert _is_chinese_content("你好 世界 你好 世界") is True

    def test_english_only(self):
        """纯英文"""
        assert _is_chinese_content("This is English content") is False

    def test_below_threshold(self):
        """低于阈值"""
        text = "中" + "a" * 10  # 1/11 < 0.3
        assert _is_chinese_content(text) is False

    def test_empty_text(self):
        """空文本"""
        assert _is_chinese_content("") is False
        assert _is_chinese_content(None) is False


class TestArticle:
    """Article 类测试"""

    def test_article_creation(self):
        """文章对象创建"""
        article = Article(
            title="测试标题",
            link="https://example.com/test",
            summary="摘要内容",
            content="<p>正文内容</p>",
            author="作者",
            source_name="来源",
            tag="标签",
        )
        assert article.title == "测试标题"
        assert article.link == "https://example.com/test"
        assert article.author == "作者"

    def test_title_strip(self):
        """标题去除首尾空白"""
        article = Article(
            title="  测试标题  ",
            link="https://example.com",
            summary="",
            content="",
        )
        assert article.title == "测试标题"

    def test_fingerprint_generated(self):
        """自动生成指纹"""
        article = Article(
            title="标题",
            link="https://example.com/article",
            summary="",
            content="",
        )
        assert article.fingerprint is not None
        assert len(article.fingerprint) == 32

    def test_default_published_time(self):
        """默认发布时间"""
        article = Article(
            title="标题",
            link="https://example.com",
            summary="",
            content="",
        )
        assert article.published is not None
        assert isinstance(article.published, datetime)

    def test_repr(self):
        """字符串表示"""
        article = Article(
            title="测试文章",
            link="https://example.com",
            summary="",
            content="",
            source_name="测试来源",
        )
        assert "测试文章" in repr(article)
        assert "测试来源" in repr(article)


class TestFetchRssFeed:
    """RSS 抓取测试（需要网络，实际运行跳过）"""

    @pytest.mark.skip(reason="需要真实网络请求或更完善的 mock")
    @patch('rss_sources.fetcher.feedparser.parse')
    @patch('rss_sources.fetcher._load_published_urls')
    def test_basic_fetch(self, mock_load_urls, mock_parse):
        """基本 RSS 抓取"""
        mock_load_urls.return_value = set()
        source = {"name": "测试源", "url": "https://example.com/rss", "tag": "测试"}
        articles = fetch_rss_feed(source)
        assert isinstance(articles, list)

    @patch('rss_sources.fetcher.feedparser.parse')
    @patch('rss_sources.fetcher._load_published_urls')
    def test_parse_error(self, mock_load_urls, mock_parse):
        """解析错误处理"""
        mock_parse.side_effect = Exception("Network error")
        source = {"name": "错误源", "url": "https://example.com/rss", "tag": ""}
        articles = fetch_rss_feed(source)
        assert articles == []

    @pytest.mark.skip(reason="mock 配置复杂，需要更完善的 fixture")
    def test_skip_already_published(self):
        """跳过已发布的文章"""
        pass
