import re
from pathlib import Path

# 检查推送脚本最终发给微信的HTML中图片URL
html = Path(r"c:\Users\lixin\WorkBuddy\Claw\wenyan_publish_preview_content.html").read_text("utf-8")

# 找所有 img 标签完整内容
imgs = re.findall(r'<img[^>]*>', html, re.DOTALL)
print(f"Total img tags: {len(imgs)}")
for i, img in enumerate(imgs):
    # 提取 src
    src_match = re.search(r'src="([^"]*)"', img)
    src = src_match.group(1) if src_match else "NO SRC"
    print(f"\n--- img {i+1} ---")
    print(f"src: {src}")
    print(f"tag: {img[:300]}")
