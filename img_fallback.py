# -*- coding: utf-8 -*-
"""
配图降级链 (Image Fallback Chain)
=================================
公众号配图按优先级自动尝试，任意一环成功即返回，全部失败则输出 prompt。

降级顺序：
  1. screenshot  — 网页截图（Crawl4ai / Playwright）
  2. doubao_40  — 豆包4.0 (doubao-seedream-4-0-250828)
  3. doubao_45  — 豆包4.5 (doubao-seedream-4-5-251128)
  4. unsplash   — Unsplash 图库搜索（免费可商用）
  5. prompt_out — 输出 prompt，人工处理

用法：
  python img_fallback.py cover "AI Agent安全指南" --style tech
  python img_fallback.py image "深蓝背景中的AI芯片特写" --size 1664x936
  python img_fallback.py batch --tasks tasks.json
"""

import os
import re
import sys
import json
import time
import logging
import argparse
import base64
import subprocess
from pathlib import Path
from typing import Optional

# ── 全局配置 ──────────────────────────────────────────────
APP_DIR = Path(__file__).parent
ENV_FILE = APP_DIR / ".env"
OUT_DIR = APP_DIR / "generated-images"
OUT_DIR.mkdir(exist_ok=True)

# 日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("img_fallback")

# ── 环境变量加载 ──────────────────────────────────────────
def load_env():
    """从 .env 加载环境变量（兼容多种格式）"""
    if not ENV_FILE.exists():
        # 尝试从 auto-push 目录找
        alt = Path(__file__).parent.parent / "20260325103711" / "wechat-auto-push" / ".env"
        if alt.exists():
            ENV_FILE.write_text(alt.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            logger.warning(f".env 未找到: {ENV_FILE}")
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()


# ════════════════════════════════════════════════════════════════════
# 豆包官方提示词构建器（来源：豆包生图技巧与API文档 2026-04-01）
# 五要素公式：主体 + 动作/状态 + 环境 + 风格 + 画质
# 进阶十要素：画风/画质/主体/环境/场景/色彩/灯光/构图/角度/比例
# ════════════════════════════════════════════════════════════════════

def build_prompt(
    subject: str,
    style: str = "tech",
    env: str = "",
    lighting: str = "",
    composition: str = "",
    color: str = "",
    quality: str = "4K高清",
) -> str:
    """
    豆包官方五要素提示词构建器。
    公式：主体 + 动作/状态 + 环境 + 风格 + 画质
    进阶十要素：画风/画质/主体/环境/场景/色彩/灯光/构图/角度/比例
    """
    parts = []
    style_map = {
        "tech": "科技感",
        "warm": "温暖治愈系",
        "business": "商业专业",
        "minimal": "极简留白",
        "creative": "创意艺术",
        "cyberpunk": "赛博朋克",
        "chinese": "古风国潮",
        "anime": "二次元动漫",
        "realistic": "照片级写实",
        "infographic": "信息图表风格",
        "poster": "海报设计",
        "concept": "概念设计",
        "macro": "微距摄影",
        "landscape": "风光摄影",
    }
    if style in style_map:
        parts.append(style_map[style])
    if quality:
        parts.append(quality)
    parts.append(subject)
    if env:
        parts.append(env)
    if color:
        parts.append(color)
    if lighting:
        parts.append(lighting)
    if composition:
        parts.append(composition)
    return "，".join(parts)


# ════════════════════════════════════════════════════════════════════
# 封面风格模板（升级版：融入五要素结构，适配公众号场景）
# ════════════════════════════════════════════════════════════════════

COVER_STYLES = {
    "tech": {
        "subject": "主标题文字居中，{title}",
        "env": "深蓝到藏青渐变背景，全息投影元素，霓虹光效，网格线装饰",
        "lighting": "冷色调，蓝色氖气灯光",
        "composition": "居中构图，主体视觉焦点，2.35:1宽幅",
        "color": "深蓝 #0a1628 到藏青 #1a3a5c 渐变",
        "quality": "4K高清，纹理清晰",
        "prompt_template": "{style}，{subject}，{env}，{lighting}，{composition}，{color}，{quality}",
    },
    "warm": {
        "subject": "主标题文字居中，{title}",
        "env": "柔和光斑，圆形虚化光圈，花卉点缀",
        "lighting": "暖色调，自然柔光",
        "composition": "居中构图，大量留白，2.35:1宽幅",
        "color": "橙色到粉色渐变，莫兰迪暖色",
        "quality": "4K高清，柔和质感",
        "prompt_template": "{style}，{subject}，{env}，{lighting}，{composition}，{color}，{quality}",
    },
    "business": {
        "subject": "主标题文字居中，{title}",
        "env": "几何线条，数据可视化元素，图表装饰",
        "lighting": "冷白光，商业摄影灯光",
        "composition": "居中构图，2.35:1宽幅",
        "color": "深灰到银白渐变，专业商务",
        "quality": "4K高清，锐利清晰",
        "prompt_template": "{style}，{subject}，{env}，{lighting}，{composition}，{color}，{quality}",
    },
    "minimal": {
        "subject": "主标题文字，\"{title}\"，艺术字体",
        "env": "细线几何装饰，极简排版",
        "lighting": "纯白光，无阴影",
        "composition": "居中构图，最大化留白，2.35:1宽幅",
        "color": "纯白背景，黑白灰主调",
        "quality": "4K高清，极简干净",
        "prompt_template": "{style}，{subject}，{env}，{lighting}，{composition}，{color}，{quality}",
    },
    "creative": {
        "subject": "主标题文字居中，{title}",
        "env": "多彩渐变背景，流体艺术元素，抽象几何",
        "lighting": "多色彩光源",
        "composition": "居中构图，视觉冲击力强，2.35:1宽幅",
        "color": "多彩渐变，视觉冲击力强",
        "quality": "4K高清，细节丰富",
        "prompt_template": "{style}，{subject}，{env}，{lighting}，{composition}，{color}，{quality}",
    },
    "cyberpunk": {
        "subject": "主标题文字，\"{title}\"，赛博朋克字体",
        "env": "赛博朋克城市夜景，霓虹招牌，雨夜街道，雾气弥漫",
        "lighting": "霓虹灯，雨夜反射光",
        "composition": "三分构图，电影感，2.35:1宽幅",
        "color": "红蓝紫霓虹撞色",
        "quality": "电影级色彩分级，4K",
        "prompt_template": "{style}，{subject}，{env}，{lighting}，{composition}，{color}，{quality}",
    },
    "chinese": {
        "subject": "主标题文字，\"{title}\"，古风书法字体",
        "env": "古风庭院，飘落花瓣，烟雾缭绕，水墨背景",
        "lighting": "自然光，古典意境",
        "composition": "居中构图，留白艺术，2.35:1宽幅",
        "color": "水墨黑白，朱红点缀",
        "quality": "工笔细腻，4K高清",
        "prompt_template": "{style}，{subject}，{env}，{lighting}，{composition}，{color}，{quality}",
    },
    "infographic": {
        "subject": "主标题文字，\"{title}\"",
        "env": "数据图表，流程图，图标装饰，干净的信息图背景",
        "lighting": "均匀白光，无阴影",
        "composition": "网格布局，信息清晰，2.35:1宽幅",
        "color": "扁平配色，品牌色系点缀",
        "quality": "高清晰度，图标锐利",
        "prompt_template": "{style}，{subject}，{env}，{lighting}，{composition}，{color}，{quality}",
    },
    "concept": {
        "subject": "主标题文字，\"{title}\"",
        "env": "科技场景，抽象背景，未来感元素",
        "lighting": "科技感蓝光",
        "composition": "居中构图，大气，2.35:1宽幅",
        "color": "深色背景，高对比科技色",
        "quality": "概念艺术级别，4K",
        "prompt_template": "{style}，{subject}，{env}，{lighting}，{composition}，{color}，{quality}",
    },
    "poster": {
        "subject": "主标题文字，\"{title}\"，大字标题",
        "env": "创意背景，现代几何图形",
        "lighting": "对比光效",
        "composition": "大字标题居中，2.35:1宽幅",
        "color": "大胆配色，高饱和度",
        "quality": "海报设计级别，4K",
        "prompt_template": "{style}，{subject}，{env}，{lighting}，{composition}，{color}，{quality}",
    },
}


def build_cover_prompt(title: str, style: str = "tech") -> str:
    """
    基于五要素模板构建封面 prompt。
    自动替换 {title} 占位符。
    """
    tpl = COVER_STYLES.get(style, COVER_STYLES["tech"])

    def render(key: str) -> str:
        return tpl.get(key, "").replace("{title}", title)

    return tpl["prompt_template"].format(
        style=tpl.get("style", ""),
        subject=render("subject"),
        env=render("env"),
        lighting=render("lighting"),
        composition=render("composition"),
        color=render("color"),
        quality=render("quality"),
    )


# ════════════════════════════════════════════════════════════
# 第一级：网页截图
# ════════════════════════════════════════════════════════════

def try_screenshot(url: str, out_name: str) -> Optional[str]:
    """
    尝试用 Crawl4ai 截图。
    url: 网页地址（如 GitHub/npm/官网）
    Returns: 图片路径，失败返回 None
    """
    if not url:
        return None

    logger.info(f"[Step1-screenshot] 尝试截图: {url}")
    out_path = OUT_DIR / f"{out_name}_screenshot.png"

    try:
        # Crawl4ai 截图
        result = subprocess.run(
            ["crwl", url, "--screenshot", str(out_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and out_path.exists() and out_path.stat().st_size > 5000:
            logger.info(f"[Step1-screenshot] ✅ 截图成功: {out_path}")
            return str(out_path)

        # Playwright 降级
        logger.info("[Step1-screenshot] Crawl4ai 失败，尝试 Playwright...")
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.screenshot(path=str(out_path), full_page=False)
            browser.close()
        if out_path.exists() and out_path.stat().st_size > 5000:
            logger.info(f"[Step1-screenshot] ✅ Playwright 截图成功: {out_path}")
            return str(out_path)
    except FileNotFoundError:
        logger.warning("[Step1-screenshot] crwl / playwright 未安装")
    except subprocess.TimeoutExpired:
        logger.warning("[Step1-screenshot] 截图超时（60s）")
    except Exception as e:
        logger.warning(f"[Step1-screenshot] 截图失败: {e}")

    return None


# ════════════════════════════════════════════════════════════
# 第二级 & 第三级：豆包生图（4.0 / 4.5）
# ════════════════════════════════════════════════════════════

def try_doubao(prompt: str, size: str, model: str, out_name: str) -> Optional[str]:
    """
    尝试用豆包 API 生图。
    model: doubao-seedream-4-0-250828 或 doubao-seedream-4-5-251128

    4.5 专有参数（来源：豆包生图API文档 2026-04-01）：
      - optimize_prompt_options.mode: standard（高质量）/ fast（快速）
      - sequential_image_generation: auto（组图模式）/ disabled（单图）
      - max_images: 1-15（组图数量）
    """
    api_key = os.getenv("ARK_API_KEY", "")
    if not api_key:
        logger.warning(f"[{model[:14]}] ARK_API_KEY 未配置，跳过")
        return None

    logger.info(f"[{model[:14]}] 尝试生图: {prompt[:60]}...")
    out_path = OUT_DIR / f"{out_name}_{model[:4]}.png"

    import requests

    w, h = map(int, size.split("x"))
    actual_pixels = w * h
    min_pixels = 3686400 if "4.5" in model else 921600

    if actual_pixels < min_pixels:
        if "4.5" in model:
            size = "2048x2048"
        else:
            size = "1664x936"
        logger.info(f"[{model[:14]}] 尺寸自动调整为: {size}")

    payload: dict = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": 1,
        "seed": -1,
        "watermark": False,
        "response_format": "b64_json",
    }

    # 4.5 专有：提示词优化（standard模式保证质量）
    if "4.5" in model:
        payload["optimize_prompt_options"] = {"mode": "standard"}

    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json=payload,
            timeout=200,
        )
        resp.raise_for_status()
        data = resp.json()

        if "data" not in data or not data["data"]:
            logger.warning(f"[{model[:14]}] 响应无图片: {str(data)[:200]}")
            return None

        img_data = data["data"][0]
        b64_str = img_data.get("b64_json") or ""
        if not b64_str:
            img_url = img_data.get("url", "")
            if img_url:
                img_resp = requests.get(img_url, timeout=60)
                img_bytes = img_resp.content
            else:
                logger.warning(f"[{model[:14]}] 无法提取图片数据")
                return None
        else:
            img_bytes = base64.b64decode(b64_str)

        out_path.write_bytes(img_bytes)
        logger.info(f"[{model[:14]}] 生图成功: {out_path} ({len(img_bytes)//1024}KB)")
        return str(out_path)

    except requests.exceptions.Timeout:
        logger.warning(f"[{model[:14]}] 请求超时（200s）")
    except requests.exceptions.HTTPError as e:
        logger.warning(f"[{model[:14]}] HTTP 错误: {e.response.status_code} {str(e)[:200]}")
    except Exception as e:
        logger.warning(f"[{model[:14]}] 生图失败: {e}")

    return None


# ════════════════════════════════════════════════════════════
# 第四级：Unsplash 图库搜索
# ════════════════════════════════════════════════════════════

def try_unsplash(query: str, out_name: str) -> Optional[str]:
    """
    从 Unsplash 免费图库搜索下载图片。
    需要 UNSPLASH_ACCESS_KEY，否则跳过。
    """
    access_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not access_key:
        logger.warning("[Step4-unsplash] UNSPLASH_ACCESS_KEY 未配置，跳过")
        return None

    logger.info(f"[Step4-unsplash] 搜索图片: {query}")
    out_path = OUT_DIR / f"{out_name}_unsplash.jpg"

    import requests

    try:
        resp = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {access_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("results"):
            logger.warning("[Step4-unsplash] 未找到匹配图片")
            return None

        photo = data["results"][0]
        download_url = photo["urls"]["regular"]
        photographer = photo.get("user", {}).get("name", "")

        img_resp = requests.get(download_url, timeout=60)
        img_resp.raise_for_status()
        out_path.write_bytes(img_resp.content)

        logger.info(
            f"[Step4-unsplash] ✅ 下载成功: {out_path} (by {photographer})"
        )
        return str(out_path)

    except requests.exceptions.HTTPError as e:
        logger.warning(f"[Step4-unsplash] HTTP 错误: {e.response.status_code}")
    except Exception as e:
        logger.warning(f"[Step4-unsplash] 搜索/下载失败: {e}")

    return None


# ════════════════════════════════════════════════════════════
# 第五级：输出 prompt 供人工处理
# ════════════════════════════════════════════════════════════

def output_prompt(prompt: str, purpose: str, out_name: str, out_dir: Path) -> str:
    """
    所有方法失败时，生成 prompt 文件供人工处理。
    """
    prompt_file = out_dir / f"{out_name}_prompt.txt"
    content = f"""# 配图失败 — 人工处理
## 用途: {purpose}
## 文件名: {out_name}

## Prompt（可直接用于豆包/DALL-E/Midjourney）:
{prompt}

## 建议尺寸:
  - 封面: 1664x710 或 2048x870（生成后裁切 900×383）
  - 内文横图: 1664x936
  - 内文竖图: 936x1664

## 使用豆包生图:
  doubao-seedream-4-0-250828 (1024x1024 最低 921600 像素)
  doubao-seedream-4-5-251128 (2048x2048 最低 3686400 像素)
"""
    prompt_file.write_text(content, encoding="utf-8")
    logger.info(f"[Step5-prompt] ⚠️ 所有方法失败，prompt 已保存: {prompt_file}")
    return str(prompt_file)


# ════════════════════════════════════════════════════════════
# 主降级链
# ════════════════════════════════════════════════════════════

def fallback_chain(
    purpose: str,
    prompt: str,
    url: Optional[str] = None,
    size: str = "1024x1024",
    style: str = "tech",
    out_name: Optional[str] = None,
    use_45: bool = True,
) -> dict:
    """
    配图降级链主函数。

    Args:
        purpose:   用途描述，如 "article_cover"、"content_img1"
        prompt:    图片描述 / 生图 prompt
        url:       可选，网页截图来源（优先尝试）
        size:      目标尺寸，如 "1664x936"
        style:     封面风格（tech/warm/business/minimal/creative/cyberpunk/chinese/infographic/concept/poster）
        out_name:  输出文件名，不传自动生成
        use_45:    封面是否优先用4.5模型（封面质量重要，默认True）
                    内文图建议 False（4.0够用，省钱省时）

    Returns:
        {"success": bool, "method": str, "path": str, "prompt_file": str}
    """
    timestamp = int(time.time())
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", purpose)[:40]
    out_name = out_name or f"{safe_name}_{timestamp}"

    logger.info(f"══════ 配图降级链启动 ══════")
    logger.info(f"  用途: {purpose}")
    logger.info(f"  Prompt: {prompt[:80]}...")
    logger.info(f"  URL: {url or '无'}")

    result: dict = {
        "success": False,
        "method": "",
        "path": None,
        "prompt_file": None,
        "prompt": prompt,
    }

    # ── Step 1: 网页截图 ──
    if url:
        path = try_screenshot(url, out_name)
        if path:
            result.update({"success": True, "method": "screenshot", "path": path})
            return result

    # ── Step 2 & 3: 豆包生图（顺序由 use_45 决定）──
    if use_45:
        # 封面路径：先4.5（质量优先），失败再4.0（省钱）
        steps = [
            ("doubao-seedream-4-5-251128", "doubao_45"),
            ("doubao-seedream-4-0-250828", "doubao_40"),
        ]
    else:
        # 内文路径：先4.0（速度+省钱），失败再4.5（质量兜底）
        steps = [
            ("doubao-seedream-4-0-250828", "doubao_40"),
            ("doubao-seedream-4-5-251128", "doubao_45"),
        ]

    for model_id, method_name in steps:
        # 4.5 最低 2048x2048，若当前尺寸更小则升级
        w, h = map(int, size.split("x"))
        adjusted_size = size
        if "4.5" in model_id and w * h < 3686400:
            adjusted_size = "2048x2048"
            logger.info(f"[{method_name}] 尺寸升级为 {adjusted_size}（满足4.5最低像素）")
        elif "4.0" in model_id and w * h < 921600:
            adjusted_size = "1664x936"
            logger.info(f"[{method_name}] 尺寸升级为 {adjusted_size}（满足4.0最低像素）")

        path = try_doubao(prompt, adjusted_size, model_id, out_name)
        if path:
            result.update({"success": True, "method": method_name, "path": path})
            return result

    # ── Step 4: Unsplash 图库 ──
    path = try_unsplash(prompt[:100], out_name)
    if path:
        result.update({"success": True, "method": "unsplash", "path": path})
        return result

    # ── Step 5: 输出 prompt ──
    pf = output_prompt(prompt, purpose, out_name, OUT_DIR)
    result.update({"success": False, "method": "prompt_out", "prompt_file": pf})
    logger.error("══════ 全部失败 ══════")
    return result



# ════════════════════════════════════════════════════════════
# 便捷封装
# ════════════════════════════════════════════════════════════

def generate_cover(
    title: str,
    style: str = "tech",
    url: Optional[str] = None,
    use_45: bool = True,
) -> dict:
    """
    生成封面图（自动降级链）。
    使用豆包官方五要素 prompt 构建器。

    Args:
        title:   文章标题
        style:   风格（tech/warm/business/minimal/creative/cyberpunk/chinese/infographic/concept/poster）
        url:     可选，优先截图
        use_45:  是否优先使用4.5模型（封面质量更重要，默认True）
    """
    full_prompt = build_cover_prompt(title, style)
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", title[:20])
    return fallback_chain(
        purpose=f"cover_{safe_name}",
        prompt=full_prompt,
        url=url,
        size="1664x710",
        style=style,
        out_name=f"cover_{safe_name}",
        use_45=use_45,
    )


def generate_content_image(
    prompt: str,
    url: Optional[str] = None,
    size: str = "1664x936",
    use_45: bool = False,
) -> dict:
    """
    生成内文图（自动降级链）。
    内文图默认4.0优先（够用 + 省钱），失败再降级到4.5。
    """
    return fallback_chain(
        purpose=f"content_img_{prompt[:30]}",
        prompt=prompt,
        url=url,
        size=size,
        use_45=use_45,
    )


def generate_batch(
    tasks: list[dict],
    delay: float = 3.0,
) -> list[dict]:
    """
    批量生成图片。
    tasks: [{"prompt": ..., "url": ..., "size": ..., "out_name": ..., "use_45": ...}, ...]
    """
    results = []
    for i, task in enumerate(tasks):
        logger.info(f"══════ 批量 {i+1}/{len(tasks)} ══════")
        r = fallback_chain(
            purpose=task.get("purpose", f"batch_{i+1}"),
            prompt=task["prompt"],
            url=task.get("url"),
            size=task.get("size", "1664x936"),
            style=task.get("style", "tech"),
            out_name=task.get("out_name"),
            use_45=task.get("use_45", True),
        )
        results.append(r)
        if i < len(tasks) - 1:
            time.sleep(delay)
    return results


# ════════════════════════════════════════════════════════════
# CLI 入口
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="配图降级链 — 截图→豆包4.0→豆包4.5→Unsplash→prompt")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # cover 子命令
    p_cover = sub.add_parser("cover", help="生成封面图")
    p_cover.add_argument("title", help="文章标题（融入封面prompt）")
    p_cover.add_argument("--style", "-s", default="tech",
                         choices=list(COVER_STYLES.keys()), help="封面风格")
    p_cover.add_argument("--url", "-u", help="优先截图的网页URL")
    p_cover.add_argument("--out", "-o", help="输出文件名")

    # image 子命令
    p_img = sub.add_parser("image", help="生成内文图")
    p_img.add_argument("prompt", help="图片描述 prompt")
    p_img.add_argument("--size", default="1664x936", help="尺寸（如 1664x936）")
    p_img.add_argument("--url", "-u", help="优先截图的网页URL")
    p_img.add_argument("--out", "-o", help="输出文件名")

    # batch 子命令
    p_batch = sub.add_parser("batch", help="批量生成（JSON文件）")
    p_batch.add_argument("--tasks", "-t", required=True, help="任务 JSON 文件路径")
    p_batch.add_argument("--delay", "-d", type=float, default=3.0, help="任务间隔（秒）")

    args = parser.parse_args()

    if args.cmd == "cover":
        r = generate_cover(args.title, style=args.style, url=args.url)
    elif args.cmd == "image":
        r = generate_content_image(args.prompt, url=args.url, size=args.size)
    elif args.cmd == "batch":
        tasks = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
        results = generate_batch(tasks, delay=args.delay)
        for i, res in enumerate(results):
            status = "✅" if res["success"] else "❌"
            print(f"{status} [{i+1}] {res['method']} -> {res.get('path') or res.get('prompt_file')}")
        sys.exit(0)

    # 打印结果
    status = "✅" if r["success"] else "❌"
    print(f"\n{status} 方法: {r['method']}")
    if r["success"]:
        print(f"📄 路径: {r['path']}")
    else:
        print(f"📄 Prompt文件: {r['prompt_file']}")
    sys.exit(0 if r["success"] else 1)
