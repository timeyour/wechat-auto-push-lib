"""
wenyan-cli 排版引擎 - Markdown → 微信公众号美化 HTML

使用 wenyan-cli (@wenyan-md/cli) 排版，输出微信编辑器兼容的内联样式 HTML。

使用方式：
    from wenyan_typesetter import render_with_wenyan

    html = render_with_wenyan("article.md", theme="pie")
    html = render_with_wenyan(text="# 标题\n正文", theme="maize")

主题列表：
    default / orangeheart / rainbow / lapis / pie / maize / purple / phycat
"""
import subprocess
import shutil
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

WENYAN_THEMES = [
    {"id": "default",     "name": "Default",      "desc": "经典蓝灰 · 简洁长文阅读"},
    {"id": "orangeheart", "name": "OrangeHeart",  "desc": "暖橙色调 · 优雅活力"},
    {"id": "rainbow",     "name": "Rainbow",      "desc": "彩虹色 · 清新活泼"},
    {"id": "lapis",       "name": "Lapis",        "desc": "冷蓝色调 · 极简清爽"},
    {"id": "pie",         "name": "Pie",          "desc": "少数派风格 · 现代锐利"},
    {"id": "maize",       "name": "Maize",        "desc": "浅黄色调 · 柔和精致"},
    {"id": "purple",      "name": "Purple",       "desc": "淡紫色调 · 干净极简"},
    {"id": "phycat",      "name": "PhyCat",       "desc": "薄荷绿 · 结构清晰"},
]
DEFAULT_THEME = "pie"


def is_wenyan_available() -> bool:
    """检查 wenyan-cli 是否已安装"""
    return shutil.which("wenyan") is not None


def render_with_wenyan(
    md_path: Optional[str] = None,
    md_text: Optional[str] = None,
    theme: str = DEFAULT_THEME,
    wechat_urls: Optional[dict] = None,
) -> str:
    """
    使用 wenyan-cli 排版 Markdown，返回微信兼容 HTML。

    参数：
        md_path: Markdown 文件路径（与 md_text 二选一）
        md_text: Markdown 文本
        theme: 主题名
        wechat_urls: 已上传到微信的图片 {key: url}，注入到 HTML 中
    """
    if not is_wenyan_available():
        raise RuntimeError("wenyan-cli 未安装。请运行: npm install -g @wenyan-md/cli")

    if theme not in [t["id"] for t in WENYAN_THEMES]:
        logger.warning(f"未知主题 '{theme}'，使用 '{DEFAULT_THEME}'")
        theme = DEFAULT_THEME

    if md_path:
        cmd = ["wenyan", "render", "-f", str(md_path), "-t", theme, "--no-footnote"]
    elif md_text:
        cmd = ["wenyan", "render", "-t", theme, "--no-footnote"]
    else:
        raise ValueError("必须提供 md_path 或 md_text")

    result = subprocess.run(
        cmd,
        input=md_text if md_text else None,
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
        shell=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"wenyan render 失败: {result.stderr}")

    html = result.stdout.strip()

    # 注入微信图片 URL
    if wechat_urls:
        for key, wechat_url in wechat_urls.items():
            img_html = (
                f'<div style="margin:20px 0;text-align:center;">'
                f'<img src="{wechat_url}" style="width:100%;max-width:680px;border-radius:8px;" alt="{key}" />'
                f'</div>'
            )
            html = html.replace(f"[IMG:{key}]", img_html)

            # 兼容 data-img-key 锚点格式
            pattern = rf'(data-img-key="{key}"[^>]*src="")'
            html = re.sub(pattern, f'data-img-key="{key}" src="{wechat_url}"', html)

    logger.info(f"wenyan 排版完成: 主题={theme}, HTML大小={len(html)/1024:.1f}KB")
    return html


def list_themes() -> list:
    """返回所有可用主题"""
    return WENYAN_THEMES


def preview_theme(md_path: str, theme: str, output_html: str):
    """渲染指定主题并保存为 HTML 预览文件"""
    html = render_with_wenyan(md_path=md_path, theme=theme)
    full = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>预览 - {theme}</title>
<style>
body {{ max-width: 680px; margin: 40px auto; padding: 0 20px; background: #fff; }}
</style>
</head>
<body>
{html}
</body>
</html>"""
    Path(output_html).write_text(full, encoding="utf-8")
    logger.info(f"预览文件已保存: {output_html}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "themes":
        print("可用主题：")
        for t in WENYAN_THEMES:
            print(f"  {t['id']:15s} {t['name']:15s} {t['desc']}")
    elif len(sys.argv) > 2:
        preview_theme(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("用法:")
        print("  python wenyan_typesetter.py themes                  # 列出所有主题")
        print("  python wenyan_typesetter.py input.md pie output.html  # 渲染预览")
