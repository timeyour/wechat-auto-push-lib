import base64
import re
from pathlib import Path

# 读取现有HTML
html = Path('article_preview.html').read_text(encoding='utf-8')

# 读取图片并转base64
def img_to_base64(path):
    data = Path(path).read_bytes()
    b64 = base64.b64encode(data).decode()
    return f'data:image/png;base64,{b64}'

# 准备两张内文图
img1_b64 = img_to_base64('generated-images/article_img1.png')
img2_b64 = img_to_base64('generated-images/article_img2.png')

# 在适当位置插入图片
# 第一张插在"一、发生了什么"之后，第二张插在"二、技术层面"之后
h2_pattern = r'(<h2[^>]*>.*?</h2>)'
matches = list(re.finditer(h2_pattern, html, re.DOTALL))

if len(matches) >= 2:
    # 第一张图插在第二个h2后面 (一、发生了什么)
    img1_html = f'<p style="text-align:center;margin:1em 0;"><img src="{img1_b64}" style="width:100%;max-width:680px;"/></p>'
    html = html[:matches[1].end()] + img1_html + html[matches[1].end():]

    # 重新找h2位置插第二张
    matches = list(re.finditer(h2_pattern, html, re.DOTALL))
    if len(matches) >= 4:
        img2_html = f'<p style="text-align:center;margin:1em 0;"><img src="{img2_b64}" style="width:100%;max-width:680px;"/></p>'
        html = html[:matches[3].end()] + img2_html + html[matches[3].end():]

Path('article_with_images.html').write_text(html, encoding='utf-8')
print('图片已嵌入: article_with_images.html')
print(f'文件大小: {len(html)/1024:.1f}KB')
