# -*- coding: utf-8 -*-
"""
配图降级链 (Image Fallback Chain) - 进化版
=================================
模块化重构：遵循单一职责原则，文件逻辑控制在 300 行以内。
"""

import re
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Optional

from image_engine.utils import logger, OUT_DIR
from image_engine.prompts import build_cover_prompt, COVER_STYLES
from image_engine.engines import try_screenshot, try_doubao, try_unsplash

def output_prompt(prompt: str, purpose: str, out_name: str) -> str:
    """所有方法失败时，生成 prompt 文件供人工处理"""
    prompt_file = OUT_DIR / f"{out_name}_prompt.txt"
    content = f"""# 配图失败 — 人工处理
## 用途: {purpose}
## 文件名: {out_name}

## Prompt（可直接用于豆包/DALL-E/Midjourney）:
{prompt}
"""
    prompt_file.write_text(content, encoding="utf-8")
    logger.info(f"[Step5-prompt] ⚠️ 所有方法失败，prompt 已保存: {prompt_file}")
    return str(prompt_file)

def fallback_chain(
    purpose: str,
    prompt: str,
    url: Optional[str] = None,
    size: str = "1024x1024",
    style: str = "tech",
    out_name: Optional[str] = None,
    use_45: bool = True,
) -> dict:
    """配图降级链主逻辑"""
    timestamp = int(time.time())
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", purpose)[:40]
    out_name = out_name or f"{safe_name}_{timestamp}"

    logger.info(f"══════ 配配图降级链启动 ══════")
    result = {"success": False, "method": "", "path": None, "prompt_file": None, "prompt": prompt}

    # 1. 截图
    if url:
        path = try_screenshot(url, out_name)
        if path:
            result.update({"success": True, "method": "screenshot", "path": path})
            return result

    # 2. 豆包 (4.5 -> 4.0 or 4.0 -> 4.5)
    steps = [
        ("doubao-seedream-4-5-251128", "doubao_45"),
        ("doubao-seedream-4-0-250828", "doubao_40"),
    ] if use_45 else [
        ("doubao-seedream-4-0-250828", "doubao_40"),
        ("doubao-seedream-4-5-251128", "doubao_45"),
    ]

    for model_id, method_name in steps:
        path = try_doubao(prompt, size, model_id, out_name)
        if path:
            result.update({"success": True, "method": method_name, "path": path})
            return result

    # 3. Unsplash
    path = try_unsplash(prompt[:100], out_name)
    if path:
        result.update({"success": True, "method": "unsplash", "path": path})
        return result

    # 4. Prompt Out
    pf = output_prompt(prompt, purpose, out_name)
    result.update({"success": False, "method": "prompt_out", "prompt_file": pf})
    return result

def generate_cover(title: str, style: str = "tech", url: Optional[str] = None) -> dict:
    full_prompt = build_cover_prompt(title, style)
    return fallback_chain(f"cover_{title[:20]}", full_prompt, url=url, size="1664x710", style=style)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="配图降级链")
    sub = parser.add_subparsers(dest="cmd", required=True)
    
    p_cover = sub.add_parser("cover", help="生成封面图")
    p_cover.add_argument("title", help="文章标题")
    p_cover.add_argument("--style", "-s", default="tech", choices=list(COVER_STYLES.keys()))
    p_cover.add_argument("--url", "-u")

    args = parser.parse_args()
    if args.cmd == "cover":
        r = generate_cover(args.title, style=args.style, url=args.url)
        print(f"\n{'✅' if r['success'] else '❌'} 方法: {r['method']}")
        print(f"📄 路径/文件: {r.get('path') or r.get('prompt_file')}")
