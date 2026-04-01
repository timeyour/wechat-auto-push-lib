"""读取 wenyan 排版好的 HTML，上传图片，推草稿"""
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
    html_file = Path(r"c:\Users\lixin\WorkBuddy\Claw\wenyan_publish_preview_content.html")
    md_dir = Path(r"c:\Users\lixin\WorkBuddy\Claw")
    title = "Anthropic 又双叒叕把源码发到 npm 上了：51 万行 Claude Code 代码泄露始末"
    cover_path = Path(r"c:\Users\lixin\WorkBuddy\Claw\generated-images\claude_leak_cover.jpg")

    log("=== wenyan publish draft ===")

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

    # 上传内文图片
    wechat_urls = {}
    if local_imgs:
        log(f"\n[2] uploading {len(local_imgs)} images...")
        for img_path in local_imgs:
            abs_path = (md_dir / img_path).resolve()
            if not abs_path.exists():
                log(f"  [WARN] not found: {img_path}")
                continue
            log(f"  uploading: {abs_path.name}...")
            try:
                with open(abs_path, "rb") as f:
                    data = publisher._request(
                        "/cgi-bin/media/uploadimg",
                        files={"media": (abs_path.name, f, "image/png")},
                    )
                if "url" in data:
                    wechat_urls[img_path] = data["url"]
                    log(f"  [OK] {abs_path.name}")
                else:
                    log(f"  [FAIL] {abs_path.name}: {data}")
            except Exception as e:
                log(f"  [ERROR] {abs_path.name}: {e}")

        # 替换图片 URL
        for local_path, wechat_url in wechat_urls.items():
            html_content = html_content.replace(f'src="{local_path}"', f'src="{wechat_url}"')
        log(f"  images replaced: {len(wechat_urls)}/{len(local_imgs)}")
    else:
        log("\n[2] no inline images")

    # 创建草稿
    log("\n[3] creating draft...")
    media_id = publisher.create_draft(
        title=title,
        content=html_content,
        thumb_media_id=thumb_media_id,
    )
    log(f"\nOK! draft created")
    log(f"  media_id: {media_id}")


if __name__ == "__main__":
    main()
