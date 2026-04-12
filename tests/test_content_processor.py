"""
content_processor 模块单元测试
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 确保可以导入项目模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from content_processor.processor import (
    clean_html,
    extract_text_summary,
    build_final_content,
    get_first_image_url,
)


class TestCleanHtml:
    """clean_html 函数测试"""

    def test_remove_script_tags(self):
        """移除 script 标签"""
        html = '<script>alert("xss")</script><p>Hello</p>'
        result = clean_html(html)
        assert '<script>' not in result
        assert 'Hello' in result

    def test_remove_style_tags(self):
        """移除 style 标签"""
        html = '<style>.hidden { display: none; }</style><p>可见内容</p>'
        result = clean_html(html)
        assert '<style>' not in result
        assert '可见内容' in result

    def test_remove_iframe(self):
        """移除 iframe 标签"""
        html = '<iframe src="https://evil.com"></iframe><p>正常内容</p>'
        result = clean_html(html)
        assert '<iframe' not in result

    def test_remove_nav_header_footer(self):
        """移除 nav, header, footer 标签"""
        html = '<nav>导航</nav><p>正文</p><footer>底部</footer>'
        result = clean_html(html)
        assert '<nav>' not in result
        assert '<footer>' not in result
        assert '正文' in result

    def test_remove_onclick_attributes(self):
        """移除 onclick 等事件属性"""
        html = '<p onclick="alert(1)">可点击段落</p>'
        result = clean_html(html)
        assert 'onclick' not in result

    def test_preserve_img_tag(self):
        """保留 img 标签的必要属性"""
        html = '<img src="test.jpg" alt="测试图片" width="100" />'
        result = clean_html(html)
        assert 'src="test.jpg"' in result
        assert 'alt="测试图片"' in result

    def test_preserve_link_tag(self):
        """保留 a 标签的 href 属性"""
        html = '<a href="https://example.com" class="external">链接</a>'
        result = clean_html(html)
        assert 'href="https://example.com"' in result

    def test_add_default_alt(self):
        """自动添加空 alt 属性"""
        html = '<img src="test.jpg" />'
        result = clean_html(html)
        assert 'alt=""' in result

    def test_apply_inline_styles(self):
        """应用微信内联样式"""
        html = '<h1>标题</h1><p>段落</p>'
        result = clean_html(html)
        assert 'font-weight:bold' in result
        assert 'font-size:' in result

    def test_empty_input(self):
        """空输入返回空字符串"""
        assert clean_html("") == ""
        assert clean_html(None) == ""  # type: ignore

    def test_chinese_content(self):
        """中文字符正确处理"""
        html = '<p>这是一段中文内容，测试特殊字符：@#$%^&*()</p>'
        result = clean_html(html)
        assert '中文' in result
        assert '特殊字符' in result


class TestExtractTextSummary:
    """extract_text_summary 函数测试"""

    def test_basic_extraction(self):
        """基本文本提取"""
        html = '<p>这是测试摘要的内容。</p>'
        result = extract_text_summary(html, max_bytes=50)
        assert '测试摘要' in result

    def test_byte_limit(self):
        """字节长度限制"""
        html = '<p>' + '中' * 50 + '</p>'
        result = extract_text_summary(html, max_bytes=20)
        encoded = result.encode('utf-8')
        assert len(encoded) <= 23  # 20 + "..."

    def test_strip_whitespace(self):
        """去除多余空白"""
        html = '<p>   测试   内容   </p>'
        result = extract_text_summary(html)
        assert '  ' not in result  # 不应有连续空格

    def test_empty_html(self):
        """空 HTML 处理"""
        assert extract_text_summary("") is not None
        assert extract_text_summary(None) is not None

    def test_html_tags_removed(self):
        """HTML 标签被移除"""
        html = '<p>测试<strong>加粗</strong>内容</p>'
        result = extract_text_summary(html)
        assert '<' not in result
        assert '测试' in result and '内容' in result


class TestBuildFinalContent:
    """build_final_content 函数测试"""

    def test_add_source_info(self):
        """添加来源信息"""
        content = '<p>原文内容</p>'
        result = build_final_content(content, source_url='https://example.com', source_name='测试来源')
        assert '来源：测试来源' in result
        assert 'https://example.com' in result

    def test_no_source(self):
        """无来源信息"""
        content = '<p>内容</p>'
        result = build_final_content(content)
        assert '<p>内容</p>' in result

    @patch('content_processor.processor.FOOTER_HTML', '<p>页脚</p>')
    def test_add_footer(self):
        """添加页脚"""
        content = '<p>正文</p>'
        result = build_final_content(content)
        assert '页脚' in result


class TestGetFirstImageUrl:
    """get_first_image_url 函数测试"""

    def test_find_first_image(self):
        """提取第一张图片"""
        html = '<p>文本</p><img src="https://example.com/img.jpg" />'
        result = get_first_image_url(html)
        assert result == 'https://example.com/img.jpg'

    def test_data_src_fallback(self):
        """data-src 降级"""
        html = '<img data-src="https://example.com/lazy.jpg" />'
        result = get_first_image_url(html)
        assert result == 'https://example.com/lazy.jpg'

    def test_no_image(self):
        """无图片返回空字符串"""
        html = '<p>无图片内容</p>'
        result = get_first_image_url(html)
        assert result == ''

    def test_empty_html(self):
        """空 HTML 处理"""
        assert get_first_image_url('') == ''
        assert get_first_image_url(None) == ''
