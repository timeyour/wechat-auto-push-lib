import re
from pathlib import Path

html = Path(r"c:\Users\lixin\WorkBuddy\Claw\wenyan_publish_preview_content.html").read_text("utf-8")

h1s = re.findall(r"<h1[^>]*>.*?</h1>", html)
print(f"H1 count: {len(h1s)}")

imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)
for i in imgs:
    print(f"IMG: {i}")

print()
print("--- first 300 chars ---")
print(html[:300])
