"""
wenyan-cli 排版引擎 - Markdown → 微信公众号美化 HTML

使用 wenyan-cli (@wenyan-md/cli) 排版，输出微信编辑器兼容的内联样式 HTML。
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from theme_library import (
    DEFAULT_THEME,
    apply_theme_profile,
    get_theme_spec,
    list_all_themes,
)

logger = logging.getLogger(__name__)


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
        theme: 主题名，可为内置主题或自定义/仿写主题 ID
        wechat_urls: 已上传到微信的图片 {key: url}，注入到 HTML 中
    """
    if not is_wenyan_available():
        raise RuntimeError("wenyan-cli 未安装。请运行: npm install -g @wenyan-md/cli")

    theme_spec = get_theme_spec(theme)
    base_theme = str(theme_spec.get("base_theme") or theme_spec["id"])
    if md_path:
        cmd = ["wenyan", "render", "-f", str(md_path), "-t", base_theme, "--no-footnote"]
    elif md_text:
        cmd = ["wenyan", "render", "-t", base_theme, "--no-footnote"]
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

    if wechat_urls:
        for key, wechat_url in wechat_urls.items():
            img_html = (
                f'<div style="margin:20px 0;text-align:center;">'
                f'<img src="{wechat_url}" style="width:100%;max-width:680px;border-radius:8px;" alt="{key}" />'
                f"</div>"
            )
            html = html.replace(f"[IMG:{key}]", img_html)
            pattern = rf'(data-img-key="{key}"[^>]*src="")'
            html = re.sub(pattern, f'data-img-key="{key}" src="{wechat_url}"', html)

    html = apply_theme_profile(html, theme_spec)
    logger.info(
        "wenyan 排版完成: theme=%s, base=%s, HTML大小=%.1fKB",
        theme_spec["id"],
        base_theme,
        len(html) / 1024,
    )
    return html


def list_themes() -> list:
    """返回所有可用主题（包含自定义/仿写主题）"""
    return list_all_themes()


def preview_theme(md_path: str, theme: str, output_html: str) -> None:
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
    logger.info("预览文件已保存: %s", output_html)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "themes":
        print("可用主题：")
        for theme in list_themes():
            print(f"  {theme['id']:20s} {theme['name']:15s} {theme['desc']}")
    elif len(sys.argv) > 3:
        preview_theme(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("用法:")
        print("  python wenyan_typesetter.py themes")
        print("  python wenyan_typesetter.py input.md pie output.html")
