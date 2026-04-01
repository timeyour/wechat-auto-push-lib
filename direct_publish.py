"""
直接推草稿到微信公众号 — 不依赖 wenyan，用 markdown 库转换

用法：
    python direct_publish.py -f article.md --title "标题" --cover cover.jpg
    python direct_publish.py -f article.md --title "标题"  # 无封面用默认图

功能：
    1. Markdown → HTML（带内联样式，适合公众号）
    2. 上传封面图到微信
    3. 扫描内文图片，上传到微信并替换URL
    4. 创建草稿
"""
import sys
import os
import re
import json
import argparse
import logging
from pathlib import Path

sys.path.insert(0, r"c:\Users\lixin\WorkBuddy\20260325103711\wechat-auto-push")

import markdown
from wechat_api.publisher import WeChatPublisher

logging.basicConfig(level=logging.INFO, format="%(message)s")
def log_info(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))

log = log_info


# ── 公众号内联样式 ──────────────────────────────
WX_STYLES = {
    "wrapper": "max-width:100%; margin:0 auto; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Microsoft YaHei', sans-serif; color:#333; font-size:16px; line-height:1.8; word-break:break-all;",
    "h1": "font-size:22px; font-weight:bold; color:#1a1a1a; margin:30px 0 20px; padding-bottom:10px; border-bottom:2px solid #333; line-height:1.4;",
    "h2": "font-size:19px; font-weight:bold; color:#1a1a1a; margin:28px 0 16px; padding-left:12px; border-left:4px solid #333; line-height:1.4;",
    "h3": "font-size:17px; font-weight:bold; color:#2a2a2a; margin:22px 0 12px; line-height:1.4;",
    "p": "margin:0 0 16px; line-height:1.8; text-align:justify;",
    "blockquote": "margin:16px 0; padding:12px 16px; border-left:4px solid #999; background:#f7f7f7; color:#555; font-size:15px;",
    "blockquote_p": "margin:0; line-height:1.8;",
    "ul": "margin:12px 0; padding-left:24px; list-style:disc;",
    "ol": "margin:12px 0; padding-left:24px; list-style:decimal;",
    "li": "margin:6px 0; line-height:1.8;",
    "strong": "color:#1a1a1a; font-weight:bold;",
    "em": "font-style:italic; color:#555;",
    "a": "color:#576b95; text-decoration:none; border-bottom:1px solid #576b95;",
    "code_inline": "background:#f0f0f0; padding:2px 6px; border-radius:3px; font-size:14px; font-family:'SF Mono',Menlo,Consolas,monospace; color:#c7254e;",
    "code_block": "background:#f6f8fa; padding:16px; border-radius:6px; font-size:14px; font-family:'SF Mono',Menlo,Consolas,monospace; overflow-x:auto; margin:16px 0; line-height:1.6; white-space:pre-wrap; word-break:break-all;",
    "table": "width:100%; border-collapse:collapse; margin:16px 0; font-size:14px;",
    "th": "background:#f0f0f0; padding:8px 12px; border:1px solid #ddd; font-weight:bold; text-align:left;",
    "td": "padding:8px 12px; border:1px solid #ddd;",
    "hr": "border:none; border-top:1px solid #ddd; margin:24px 0;",
    "img": "max-width:100%; height:auto; border-radius:4px; margin:16px 0; display:block;",
}

WRAPPER_CSS = WX_STYLES["wrapper"]


def md_to_wx_html(md_text: str) -> str:
    """Markdown → 带内联样式的 HTML，适配公众号"""
    # 用 markdown 库转换
    extensions = ["tables", "fenced_code", "nl2br"]
    body_html = markdown.markdown(md_text, extensions=extensions)

    # 把内联样式注入各标签
    body_html = inject_styles(body_html)

    # 包装成完整 HTML
    full_html = f'<section style="{WRAPPER_CSS}">{body_html}</section>'
    return full_html


def inject_styles(html: str) -> str:
    """给 HTML 标签注入内联样式"""
    import re

    # h1
    html = re.sub(
        r"<h1>",
        f'<h1 style="{WX_STYLES["h1"]}">',
        html,
    )
    # h2
    html = re.sub(
        r"<h2>",
        f'<h2 style="{WX_STYLES["h2"]}">',
        html,
    )
    # h3
    html = re.sub(
        r"<h3>",
        f'<h3 style="{WX_STYLES["h3"]}">',
        html,
    )
    # p (跳过 blockquote 内部的 p)
    html = re.sub(
        r"<p>",
        f'<p style="{WX_STYLES["p"]}">',
        html,
    )
    # blockquote
    html = re.sub(
        r"<blockquote>",
        f'<blockquote style="{WX_STYLES["blockquote"]}">',
        html,
    )
    # strong
    html = re.sub(
        r"<strong>",
        f'<strong style="{WX_STYLES["strong"]}">',
        html,
    )
    # em
    html = re.sub(
        r"<em>",
        f'<em style="{WX_STYLES["em"]}">',
        html,
    )
    # a
    html = re.sub(
        r'<a href="([^"]*)"',
        rf'<a href="\1" style="{WX_STYLES["a"]}"',
        html,
    )
    # inline code
    html = re.sub(
        r"<code>(?!.*<pre>)",
        f'<code style="{WX_STYLES["code_inline"]}">',
        html,
    )
    # pre > code block
    def style_code_block(m):
        return f'<pre style="{WX_STYLES["code_block"]}">{m.group(1)}</pre>'

    html = re.sub(r"<pre><code>(.*?)</code></pre>", style_code_block, html, flags=re.DOTALL)

    # table
    html = re.sub(
        r"<table>",
        f'<table style="{WX_STYLES["table"]}">',
        html,
    )
    html = re.sub(
        r"<th>",
        f'<th style="{WX_STYLES["th"]}">',
        html,
    )
    html = re.sub(
        r"<td>",
        f'<td style="{WX_STYLES["td"]}">',
        html,
    )
    # hr
    html = re.sub(
        r"<hr\s*/?>",
        f'<hr style="{WX_STYLES["hr"]}">',
        html,
    )
    # img
    html = re.sub(
        r'<img src="([^"]*)"([^>]*)>',
        rf'<img src="\1"\2 style="{WX_STYLES["img"]}">',
        html,
    )
    # ul / ol
    html = re.sub(
        r"<ul>",
        f'<ul style="{WX_STYLES["ul"]}">',
        html,
    )
    html = re.sub(
        r"<ol>",
        f'<ol style="{WX_STYLES["ol"]}">',
        html,
    )
    # li
    html = re.sub(
        r"<li>",
        f'<li style="{WX_STYLES["li"]}">',
        html,
    )

    return html


def scan_local_images(md_path: Path) -> dict:
    """从 Markdown 扫描本地图片引用"""
    md_dir = md_path.parent
    md_text = md_path.read_text(encoding="utf-8")
    pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
    images = {}

    for match in re.finditer(pattern, md_text):
        img_path = match.group(2).strip()
        if img_path.startswith("http://") or img_path.startswith("https://"):
            continue
        abs_path = (md_dir / img_path).resolve()
        if abs_path.exists():
            images[img_path] = abs_path
        else:
            log(f"  [WARN] 图片不存在: {img_path}")

    return images


def upload_images_to_wechat(publisher, local_images: dict) -> dict:
    """上传本地图片到微信，返回 {原始路径: 微信URL}"""
    from wechat_api.publisher import API_BASE

    wechat_urls = {}
    token = publisher.token_manager.get_access_token()
    url = f"{API_BASE}/cgi-bin/media/uploadimg"

    for rel_path, abs_path in local_images.items():
        log(f"  上传: {abs_path.name} ...")
        try:
            with open(abs_path, "rb") as f:
                data = publisher._request(
                    "/cgi-bin/media/uploadimg",
                    files={"media": (abs_path.name, f, "image/png")},
                )
            if "url" in data:
                wechat_urls[rel_path] = data["url"]
                log(f"  [OK] {abs_path.name}")
            else:
                log(f"  [FAIL] {abs_path.name}: {data}")
        except Exception as e:
            log(f"  [ERROR] {abs_path.name}: {e}")

    return wechat_urls


def replace_image_urls(html: str, wechat_urls: dict) -> str:
    """替换 HTML 中的本地图片路径为微信 URL"""
    result = html
    for local_path, wechat_url in wechat_urls.items():
        filename = Path(local_path).name
        result = result.replace(f'src="{local_path}"', f'src="{wechat_url}"')
        pattern = rf'(src="[^"]*){re.escape(filename)}([^"]*")'
        result = re.sub(pattern, rf'src="{wechat_url}"', result)
    return result


def main():
    parser = argparse.ArgumentParser(description="直接推草稿到公众号")
    parser.add_argument("--file", "-f", required=True, help="Markdown 文件路径")
    parser.add_argument("--title", help="文章标题（默认用 MD 第一行）")
    parser.add_argument("--cover", help="封面图路径（可选）")
    parser.add_argument("--author", default="", help="作者名")
    args = parser.parse_args()

    md_path = Path(args.file)
    if not md_path.exists():
        log(f"文件不存在: {md_path}")
        sys.exit(1)

    # 标题
    title = args.title
    if not title:
        first_line = md_path.read_text(encoding="utf-8").split("\n")[0].lstrip("#").strip()
        title = first_line

    log("=" * 50)
    log(f"直接推草稿")
    log(f"  文件: {md_path.name}")
    log(f"  标题: {title}")
    log("=" * 50)

    # Step 1: 扫描图片
    log("\n[1/5] 扫描本地图片...")
    local_images = scan_local_images(md_path)
    log(f"  找到 {len(local_images)} 张图片")

    # Step 2: MD → HTML
    log("\n[2/5] Markdown → HTML...")
    md_text = md_path.read_text(encoding="utf-8")
    html_content = md_to_wx_html(md_text)
    log(f"  HTML: {len(html_content)/1024:.1f}KB")

    # Step 3: 封面图
    log("\n[3/5] 处理封面图...")
    from dotenv import load_dotenv
    load_dotenv(Path(r"c:\Users\lixin\WorkBuddy\20260325103711\wechat-auto-push\.env"))
    publisher = WeChatPublisher()

    cover_path = None
    if args.cover:
        cover_path = Path(args.cover)
        if not cover_path.exists():
            log(f"  [WARN] 封面不存在: {cover_path}")

    if cover_path and cover_path.exists():
        thumb_media_id = publisher.upload_thumb_image(cover_path)
    else:
        log("  使用默认封面图...")
        from config import DEFAULT_COVER_MEDIA_ID
        thumb_media_id = DEFAULT_COVER_MEDIA_ID

    if not thumb_media_id:
        log("[ERROR] 无封面图可用，请通过 --cover 指定或配置 DEFAULT_COVER_MEDIA_ID")
        sys.exit(1)

    log(f"  封面 media_id: {thumb_media_id}")

    # Step 4: 上传内文图片
    if local_images:
        log(f"\n[4/5] 上传 {len(local_images)} 张图片到微信...")
        wechat_urls = upload_images_to_wechat(publisher, local_images)
        html_content = replace_image_urls(html_content, wechat_urls)
        log(f"  上传完成: {len(wechat_urls)}/{len(local_images)}")
    else:
        log("\n[4/5] 无内文图片")

    # Step 5: 创建草稿
    log("\n[5/5] 创建草稿...")
    media_id = publisher.create_draft(
        title=title,
        content=html_content,
        thumb_media_id=thumb_media_id,
        author=args.author,
    )
    log(f"\n✅ 草稿创建成功！")
    log(f"  media_id: {media_id}")
    log(f"  去公众号后台 > 草稿箱 查看")


if __name__ == "__main__":
    main()
