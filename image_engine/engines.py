# -*- coding: utf-8 -*-
import base64
import os
import subprocess
from typing import Optional

import requests

from .utils import OUT_DIR, logger


def try_screenshot(url: str, out_name: str) -> Optional[str]:
    """尝试用 Crawl4ai 或 Playwright 截图"""
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
    except Exception as e:
        logger.warning(f"[Step1-screenshot] 截图失败: {e}")

    return None

def try_doubao(prompt: str, size: str, model: str, out_name: str) -> Optional[str]:
    """尝试用豆包 API 生图"""
    api_key = os.getenv("ARK_API_KEY", "")
    if not api_key:
        logger.warning(f"[{model[:14]}] ARK_API_KEY 未配置，跳过")
        return None

    logger.info(f"[{model[:14]}] 尝试生图: {prompt[:60]}...")
    out_path = OUT_DIR / f"{out_name}_{model[:4]}.png"

    w, h = map(int, size.split("x"))
    actual_pixels = w * h
    min_pixels = 3686400 if "4.5" in model else 921600

    if actual_pixels < min_pixels:
        size = "2048x2048" if "4.5" in model else "1664x936"
        logger.info(f"[{model[:14]}] 尺寸自动调整为: {size}")

    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": 1,
        "seed": -1,
        "watermark": False,
        "response_format": "b64_json",
    }

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
                return None
        else:
            img_bytes = base64.b64decode(b64_str)

        out_path.write_bytes(img_bytes)
        logger.info(f"[{model[:14]}] 生图成功: {out_path} ({len(img_bytes)//1024}KB)")
        return str(out_path)
    except Exception as e:
        logger.warning(f"[{model[:14]}] 生图失败: {e}")

    return None

def try_unsplash(query: str, out_name: str) -> Optional[str]:
    """从 Unsplash 免费图库搜索下载图片"""
    access_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not access_key:
        logger.warning("[Step4-unsplash] UNSPLASH_ACCESS_KEY 未配置，跳过")
        return None

    logger.info(f"[Step4-unsplash] 搜索图片: {query}")
    out_path = OUT_DIR / f"{out_name}_unsplash.jpg"

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
        img_resp = requests.get(download_url, timeout=60)
        img_resp.raise_for_status()
        out_path.write_bytes(img_resp.content)

        logger.info(f"[Step4-unsplash] ✅ 下载成功: {out_path}")
        return str(out_path)
    except Exception as e:
        logger.warning(f"[Step4-unsplash] 搜索/下载失败: {e}")

    return None
