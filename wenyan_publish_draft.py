"""
wenyan 排版 + 微信图片上传 + 推草稿 — 一键流程

用法：
    python wenyan_publish_draft.py -f article.md --title "标题" --cover cover.jpg [--theme pie]

流程：
    1. 去掉 MD 中的 H1 标题（公众号标题由后台管理）
    2. 用 wenyan 排版 Markdown → 美化 HTML
    3. 上传本地图片到微信，替换 HTML 中的图片路径
    4. 上传封面图
    5. 创建草稿
"""
import sys
import os
import re
import json
import argparse
import subprocess
from pathlib import Path

sys.path.insert(0, r"c:\Users\lixin\WorkBuddy\20260325103711\wechat-auto-push")

from dotenv import load_dotenv
load_dotenv(Path(r"c:\Users\lixin\WorkBuddy\20260325103711\wechat-auto-push\.env"))

from wechat_api.publisher import WeChatPublisher


def log(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))


WENYAN_CMD = r"C:\home\cxc\.npm-global\wenyan.cmd"


def render_wenyan(md_file: str, theme: str = "pie") -> str:
    """调用 wenyan render 排版，返回纯 HTML（不含外层 wrapper）"""
    result = subprocess.run(
        [WENYAN_CMD, "render", "-f", md_file, "-t", theme, "--no-footnote"],
        capture_output=True,
        text=True,
        timeout=120,
        encoding="utf-8",
        shell=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"wenyan render failed: {result.stderr}")
    return result.stdout.strip()


def strip_h1(md_text: str) -> str:
    """去掉 Markdown 中的 H1 标题行（公众号标题由后台管理，正文不重复）"""
    lines = md_text.split("\n")
    stripped = []
    for line in lines:
        if re.match(r"^#\s+.+", line.strip()):
            log(f"  [SKIP] H1: {line.strip()[:60]}")
            continue
        stripped.append(line)
    return "\n".join(stripped)


def scan_local_images(md_text: str, md_dir: Path) -> dict:
    """扫描 Markdown 中的本地图片引用"""
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
            log(f"  [WARN] image not found: {img_path}")
    return images


def upload_images_to_wechat(publisher, local_images: dict) -> dict:
    """上传本地图片到微信，返回 {原始路径: 微信URL}"""
    wechat_urls = {}
    for rel_path, abs_path in local_images.items():
        log(f"  uploading: {abs_path.name} ...")
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
        # 替换 src="本地路径"
        result = result.replace(f'src="{local_path}"', f'src="{wechat_url}"')
        # 替换含文件名的路径
        pattern = rf'(src="[^"]*){re.escape(filename)}([^"]*")'
        result = re.sub(pattern, rf'src="{wechat_url}"', result)
    return result


def main():
    parser = argparse.ArgumentParser(description="wenyan 排版 + 推草稿到公众号")
    parser.add_argument("--file", "-f", required=True, help="Markdown 文件路径")
    parser.add_argument("--title", help="文章标题（默认用 MD 第一行 H1）")
    parser.add_argument("--cover", help="封面图路径（可选）")
    parser.add_argument("--author", default="", help="作者名")
    parser.add_argument("--theme", default="pie", help="wenyan 主题 (default/orangeheart/rainbow/lapis/pie/maize/purple/phycat)")
    args = parser.parse_args()

    md_path = Path(args.file)
    if not md_path.exists():
        log(f"File not found: {md_path}")
        sys.exit(1)

    # 从 H1 提取标题
    title = args.title
    if not title:
        first_line = md_path.read_text(encoding="utf-8").split("\n")[0].lstrip("#").strip()
        if first_line:
            title = first_line

    log("=" * 50)
    log(f"wenyan + publish")
    log(f"  file: {md_path.name}")
    log(f"  title: {title}")
    log(f"  theme: {args.theme}")
    log("=" * 50)

    # Step 1: 读取 MD，去掉 H1
    log("\n[1/6] reading markdown & stripping H1...")
    md_text = md_path.read_text(encoding="utf-8")
    md_no_h1 = strip_h1(md_text)
    # 写入临时文件
    tmp_md = md_path.with_suffix(".noh1.md")
    tmp_md.write_text(md_no_h1, encoding="utf-8")

    # Step 2: 扫描图片
    log("\n[2/6] scanning local images...")
    local_images = scan_local_images(md_no_h1, md_path.parent)
    log(f"  found {len(local_images)} images")

    # Step 3: wenyan 排版
    log(f"\n[3/6] wenyan render (theme={args.theme})...")
    html_content = render_wenyan(str(tmp_md), args.theme)
    log(f"  HTML: {len(html_content)/1024:.1f}KB")

    # Step 4: 封面图
    log("\n[4/6] uploading cover...")
    publisher = WeChatPublisher()
    cover_path = None
    if args.cover:
        cover_path = Path(args.cover)
        if not cover_path.exists():
            log(f"  [WARN] cover not found: {cover_path}")

    if cover_path and cover_path.exists():
        thumb_media_id = publisher.upload_thumb_image(cover_path)
    else:
        log("  using default cover...")
        from config import DEFAULT_COVER_MEDIA_ID
        thumb_media_id = DEFAULT_COVER_MEDIA_ID

    if not thumb_media_id:
        log("[ERROR] no cover available")
        sys.exit(1)
    log(f"  cover media_id: {thumb_media_id}")

    # Step 5: 上传内文图片并替换 URL
    if local_images:
        log(f"\n[5/6] uploading {len(local_images)} images to wechat...")
        wechat_urls = upload_images_to_wechat(publisher, local_images)
        html_content = replace_image_urls(html_content, wechat_urls)
        log(f"  uploaded: {len(wechat_urls)}/{len(local_images)}")
    else:
        log("\n[5/6] no inline images")

    # Step 6: 创建草稿
    log("\n[6/6] creating draft...")
    media_id = publisher.create_draft(
        title=title,
        content=html_content,
        thumb_media_id=thumb_media_id,
        author=args.author,
    )
    log(f"\nOK! draft created")
    log(f"  media_id: {media_id}")
    log(f"  check wechat admin > drafts")

    # 清理临时文件
    if tmp_md.exists():
        tmp_md.unlink()


if __name__ == "__main__":
    main()
