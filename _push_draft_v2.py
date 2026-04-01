"""wenyan排版 + 上传图片 + 推草稿（带调试）"""
import sys
import re
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


def main():
    html_file = Path(r"c:\Users\lixin\WorkBuddy\Claw\wenyan_publish_v2_content.html")
    md_dir = Path(r"c:\Users\lixin\WorkBuddy\Claw")
    title = "Anthropic \u53c8\u53cc\u53d2\u53d5\u628a\u6e90\u7801\u53d1\u5230 npm \u4e0a\u4e86\uff1a51 \u4e07\u884c Claude Code \u4ee3\u7801\u6cc4\u9732\u59cb\u672b"
    cover_path = Path(r"c:\Users\lixin\WorkBuddy\Claw\generated-images\claude_leak_cover_v2_900x383.jpg")

    # 读取 wenyan 排版后的 HTML
    html_content = html_file.read_text("utf-8")
    log(f"HTML loaded: {len(html_content)/1024:.1f}KB")

    # 初始化 publisher
    publisher = WeChatPublisher()

    # 上传封面
    log("\n[1] uploading cover...")
    thumb_media_id = publisher.upload_thumb_image(cover_path)
    log(f"  cover media_id: {thumb_media_id}")

    # 扫描 HTML 中的本地图片路径
    local_imgs = re.findall(r'<img[^>]+src="([^"]+)"', html_content)
    local_imgs = [p for p in local_imgs if not p.startswith("http")]
    log(f"\n  Found {len(local_imgs)} local images:")
    for p in local_imgs:
        log(f"    {p}")

    # 上传内文图片
    wechat_urls = {}
    if local_imgs:
        log(f"\n[2] uploading {len(local_imgs)} images to wechat...")
        for img_path in local_imgs:
            abs_path = (md_dir / img_path).resolve()
            if not abs_path.exists():
                log(f"  [WARN] not found: {img_path} -> {abs_path}")
                continue
            log(f"  uploading: {abs_path.name} ({abs_path.stat().st_size/1024:.0f}KB)...")
            try:
                with open(abs_path, "rb") as f:
                    data = publisher._request(
                        "/cgi-bin/media/uploadimg",
                        files={"media": (abs_path.name, f, "image/png")},
                    )
                if "url" in data:
                    wechat_urls[img_path] = data["url"]
                    log(f"  [OK] {abs_path.name} -> {data['url']}")
                else:
                    log(f"  [FAIL] {abs_path.name}: {data}")
            except Exception as e:
                log(f"  [ERROR] {abs_path.name}: {e}")

        # 替换图片 URL - 逐个替换并验证
        log(f"\n[3] replacing image URLs...")
        for local_path, wechat_url in wechat_urls.items():
            before_count = html_content.count(local_path)
            html_content = html_content.replace(local_path, wechat_url)
            after_count = html_content.count(local_path)
            log(f"  {local_path}")
            log(f"    -> {wechat_url}")
            log(f"    replaced: {before_count - after_count} occurrences")
        
        # 最终验证 - 确保没有残留的本地路径
        remaining = re.findall(r'<img[^>]+src="([^"]+)"', html_content)
        remaining_local = [r for r in remaining if not r.startswith("http") and not r.startswith("//")]
        if remaining_local:
            log(f"\n  [WARN] still have local paths: {remaining_local}")
        else:
            log(f"\n  [OK] all images use wechat URLs")

        # 打印最终 img 标签
        final_imgs = re.findall(r'<img[^>]+>', html_content)
        for img in final_imgs:
            log(f"  final: {img[:200]}")
    else:
        log("\n[2] no inline images")

    # 创建草稿
    log("\n[4] creating draft...")
    media_id = publisher.create_draft(
        title=title,
        content=html_content,
        thumb_media_id=thumb_media_id,
    )
    log(f"\nOK! draft created")
    log(f"  media_id: {media_id}")


if __name__ == "__main__":
    main()
