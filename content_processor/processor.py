"""
内容处理模块 - HTML 清洗、格式转换、图片下载、封面生成
"""
from __future__ import annotations

import hashlib
import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Comment

from config import DIGEST_MAX_BYTES, FOOTER_HTML, COVER_CACHE

if TYPE_CHECKING:
    from PIL import ImageFont

logger = logging.getLogger(__name__)

REMOVE_TAGS = {"script", "style", "iframe", "noscript", "svg", "form",
               "input", "button", "textarea", "select", "nav", "header", "footer"}


def clean_html(html_content: str) -> str:
    """
    清洗 HTML 内容使其适配微信公众号格式。
    移除脚本、样式、外部事件属性，添加内联样式。
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "lxml")

    # 移除不需要的标签
    for tag_name in REMOVE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # 移除注释
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # 清理标签属性（只保留必要属性）
    for tag in soup.find_all(True):
        tag_name = tag.name
        if tag_name == "img":
            allowed = {"src", "alt", "width", "data-src"}
        elif tag_name == "a":
            allowed = {"href"}
        elif tag_name in ("p", "div", "section", "span", "h1", "h2", "h3", "h4", "h5", "h6",
                          "ul", "ol", "li", "blockquote", "pre", "code", "br", "hr", "strong", "em"):
            allowed = set()
        elif tag_name in ("table", "tr", "td", "th"):
            allowed = {"border", "cellpadding", "cellspacing", "width"}
        elif tag_name == "video":
            allowed = {"src", "width"}
        elif tag_name == "source":
            allowed = {"src", "type"}
        else:
            allowed = set()

        to_remove = [a for a in tag.attrs if a not in allowed or a.startswith("on")]
        for a in to_remove:
            del tag[a]

    # 确保图片有 alt 属性
    for img in soup.find_all("img"):
        if not img.get("alt"):
            img["alt"] = ""

    _apply_wechat_styles(soup)
    return str(soup)


def _apply_wechat_styles(soup: BeautifulSoup):
    """为内容添加适合微信阅读的内联样式"""
    for i in range(1, 4):
        for tag in soup.find_all(f"h{i}"):
            tag["style"] = f"font-weight:bold;font-size:{20-i*2}px;margin:20px 0 10px 0;color:#333;"

    for tag in soup.find_all("p"):
        if not tag.get("style"):
            tag["style"] = "margin:10px 0;line-height:1.8;color:#333;font-size:15px;"

    for tag in soup.find_all("blockquote"):
        tag["style"] = "margin:15px 0;padding:10px 15px;border-left:3px solid #ddd;background:#f7f7f7;color:#666;font-size:14px;"

    for tag in soup.find_all("pre"):
        tag["style"] = "background:#f5f5f5;padding:15px;border-radius:4px;overflow-x:auto;font-size:13px;"

    for tag in soup.find_all("code"):
        if not (tag.parent and tag.parent.name == "pre"):
            tag["style"] = "background:#f0f0f0;padding:2px 5px;border-radius:3px;font-size:13px;"

    for tag in soup.find_all("img"):
        if not tag.get("style"):
            tag["style"] = "max-width:100%;height:auto;display:block;margin:15px auto;"

    for tag in soup.find_all("a"):
        if not tag.get("style"):
            tag["style"] = "color:#576b95;text-decoration:none;"


def extract_text_summary(html_content: str, max_bytes: Optional[int] = None) -> str:
    """从 HTML 中提取纯文本摘要（限制字节数）"""
    if max_bytes is None:
        max_bytes = DIGEST_MAX_BYTES
    soup = BeautifulSoup(html_content or "", "lxml")
    text = re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True)).strip()
    encoded = text.encode("utf-8")[:max_bytes]
    return encoded.decode("utf-8", errors="ignore") + "..."


def build_final_content(
    article_content: str,
    source_url: str = "",
    source_name: str = ""
) -> str:
    """构建最终发布内容（来源信息 + 页脚）"""
    content = article_content
    if source_url:
        content += (
            f'<section style="margin-top:20px;padding:10px;background:#f7f7f7;'
            f'border-radius:4px;font-size:13px;color:#666;">'
            f'<p>来源：{source_name or "网络"} | <a href="{source_url}" style="color:#576b95;">查看原文</a></p>'
            f'</section>'
        )
    if FOOTER_HTML:
        content += FOOTER_HTML
    return content


def _get_font_path(size: int = 36) -> "ImageFont.FreeTypeFont":  # type: ignore[name-defined]
    """
    跨平台获取中文字体。

    Windows: C:/Windows/Fonts/
    Mac: /System/Library/Fonts/, ~/Library/Fonts/
    Linux: /usr/share/fonts/, ~/.fonts/

    Returns:
        PIL ImageFont 对象

    Raises:
        所有字体都不可用时返回默认字体
    """
    from PIL import ImageFont
    import platform
    import os

    system = platform.system()

    # 候选字体列表（按优先级排序）
    if system == "Windows":
        font_dirs = [
            Path("C:/Windows/Fonts"),
        ]
        font_names = ["msyh.ttc", "simhei.ttf", "simsun.ttc", "msyhbd.ttc"]
    elif system == "Darwin":  # macOS
        font_dirs = [
            Path("/System/Library/Fonts"),
            Path("/Library/Fonts"),
            Path.home() / "Library/Fonts",
        ]
        font_names = ["PingFang.ttc", "Hiragino Sans GB.ttc", "STHeiti Light.ttc",
                      "Arial Unicode.ttf", "SimHei.ttc"]
    else:  # Linux
        font_dirs = [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path.home() / ".fonts",
            Path.home() / ".local/share/fonts",
        ]
        font_names = ["NotoSansCJK-Regular.ttc", "WenQuanYi Micro Hei.ttc",
                      "Droid Sans Fallback.ttf", "Source Han Sans CN Regular.otf"]

    # 递归搜索字体目录
    def find_fonts():
        for font_dir in font_dirs:
            if not font_dir.exists():
                continue
            # 递归查找所有 .ttc 和 .ttf 文件
            for ext in ["*.ttc", "*.ttf", "*.otf"]:
                for font_path in font_dir.rglob(ext):
                    yield font_path

    # 尝试加载候选字体
    for font_path in find_fonts():
        try:
            font = ImageFont.truetype(str(font_path), size)
            logger.debug(f"成功加载字体: {font_path}")
            return font
        except Exception:
            continue

    # 所有字体都不可用，返回默认字体
    logger.warning("未找到合适的中文字体，使用系统默认字体")
    return ImageFont.load_default()


def generate_default_cover(title: str = "公众号文章") -> Path:
    """
    生成默认封面图（渐变背景 + 标题文字）
    微信封面要求：2.35:1 比例，建议 900×383 像素，不超过 2MB
    """
    from PIL import Image, ImageDraw

    width, height = 900, 383
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # 渐变背景（深蓝 → 紫色）
    for y in range(height):
        ratio = y / height
        r = int(30 + ratio * 60)
        g = int(30 + ratio * 20)
        b = int(80 + ratio * 80)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 加载中文字体（跨平台）
    font = _get_font_path(36)

    # 截断标题
    display_title = title[:18] + "..." if len(title) > 18 else title

    # 绘制标题（居中）
    try:
        bbox = draw.textbbox((0, 0), display_title, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = (width - tw) // 2, (height - th) // 2 - 20
    except Exception:
        x, y = 100, height // 2 - 20

    draw.text((x + 2, y + 2), display_title, fill=(0, 0, 0), font=font)
    draw.text((x, y), display_title, fill=(255, 255, 255), font=font)

    # 底部品牌文字
    brand_font = _get_font_path(18)
    draw.text((width // 2 - 40, height - 40), "公众号", fill=(180, 180, 200), font=brand_font)

    save_path = COVER_CACHE / "default_cover.jpg"
    img.save(save_path, "JPEG", quality=85)
    logger.info(f"默认封面已生成: {save_path}")
    return save_path


def download_image(url: str, save_path: Optional[Path] = None) -> Path:
    """
    下载图片到本地缓存，自动转换 webp/bmp 等格式为 JPEG。
    超过 1.8MB 则压缩。
    """
    if not url:
        raise ValueError("URL 为空")

    filename = f"{hash(url) % 100000000:08d}.jpg"
    save_path = save_path or COVER_CACHE / filename

    if save_path.exists():
        return save_path

    resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    raw_data = resp.content

    needs_convert = Path(urlparse(url).path).suffix.lower() in (".webp", ".bmp", ".tiff", ".svg", ".avif")

    if needs_convert or len(raw_data) > 1.8 * 1024 * 1024:
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(raw_data))
            if img.mode in ("RGBA", "P", "LA", "PA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                if img.mode in ("RGBA", "LA", "PA"):
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                else:
                    img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")
            img.save(save_path, "JPEG", quality=75, optimize=True)
            if needs_convert:
                logger.info(f"格式转换: {Path(urlparse(url).path).suffix} -> jpg")
            else:
                logger.info(f"图片已压缩: {save_path.name}")
        except Exception as e:
            logger.warning(f"PIL 处理失败: {e}，保存原始数据")
            save_path.write_bytes(raw_data)
    else:
        save_path.write_bytes(raw_data)
        logger.info(f"图片下载成功: {save_path.name}")

    return save_path


def get_first_image_url(html_content: str) -> str:
    """从 HTML 内容中提取第一张图片的 URL"""
    soup = BeautifulSoup(html_content or "", "lxml")
    img = soup.find("img")
    if img:
        return img.get("src", "") or img.get("data-src", "")
    return ""
