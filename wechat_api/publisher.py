"""
微信公众号 API 模块 - Token 管理、图片上传、草稿创建
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import requests
from wechatpy import WeChatClient

from config import (
    WECHAT_APPID,
    WECHAT_APPSECRET,
    TOKEN_CACHE_FILE,
    API_BASE,
    MAX_THUMB_SIZE_BYTES,
    REQUEST_TIMEOUT,
    IMAGE_UPLOAD_TIMEOUT,
    DIGEST_MAX_BYTES,
    TITLE_MAX_BYTES,
    TITLE_DISPLAY_LENGTH,
)

logger = logging.getLogger(__name__)


class TokenManager:
    """微信 Access Token 管理（带文件缓存）"""

    def __init__(self, appid: str, secret: str):
        self.appid = appid
        self.secret = secret
        self._access_token = ""
        self._expires_at = 0

    def get_access_token(self) -> str:
        """获取有效的 access_token，优先使用缓存"""
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token
        if self._load_cache():
            return self._access_token
        self._refresh_token()
        return self._access_token

    def _refresh_token(self):
        """刷新 access_token"""
        resp = requests.get(
            f"{API_BASE}/cgi-bin/token",
            params={"grant_type": "client_credential", "appid": self.appid, "secret": self.secret},
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(f"获取 access_token 失败: {data.get('errmsg', '未知错误')}")
        self._access_token = data["access_token"]
        self._expires_at = time.time() + data.get("expires_in", 7200)
        self._save_cache()
        logger.info("access_token 刷新成功")

    def _save_cache(self):
        TOKEN_CACHE_FILE.write_text(
            json.dumps({"access_token": self._access_token, "expires_at": self._expires_at}),
            encoding="utf-8",
        )

    def _load_cache(self) -> bool:
        if not TOKEN_CACHE_FILE.exists():
            return False
        try:
            cache = json.loads(TOKEN_CACHE_FILE.read_text(encoding="utf-8"))
            if time.time() < cache.get("expires_at", 0) - 60:
                self._access_token = cache["access_token"]
                self._expires_at = cache["expires_at"]
                logger.info("从缓存加载 access_token")
                return True
        except (json.JSONDecodeError, KeyError):
            pass
        return False


class WeChatPublisher:
    """微信公众号发布器"""

    def __init__(self, appid: str = None, secret: str = None):
        self.appid = appid or WECHAT_APPID
        self.secret = secret or WECHAT_APPSECRET
        if not self.appid or not self.secret:
            raise ValueError("请设置 WECHAT_APPID 和 WECHAT_APPSECRET 环境变量")
        self.token_manager = TokenManager(self.appid, self.secret)
        self.client = WeChatClient(self.appid, self.secret)

    def _request(self, path: str, method: str = "POST", data: dict = None,
                 params: dict = None, files: dict = None) -> dict:
        """统一 API 请求方法，自动处理 token 过期"""
        token = self.token_manager.get_access_token()
        url = f"{API_BASE}{path}"
        if params is None:
            params = {}
        params["access_token"] = token

        if method == "GET":
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        elif method == "POST" and files:
            resp = requests.post(url, params=params, data=data, files=files, timeout=IMAGE_UPLOAD_TIMEOUT)
        else:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            resp = requests.post(
                url, params=params, data=body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=REQUEST_TIMEOUT,
            )

        result = resp.json()

        # Token 过期自动刷新重试
        if result.get("errcode") == 40001:
            logger.warning("access_token 已过期，刷新重试...")
            self.token_manager._refresh_token()
            params["access_token"] = self.token_manager.get_access_token()
            if method == "GET":
                resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            elif method == "POST" and files:
                resp = requests.post(url, params=params, data=data, files=files, timeout=IMAGE_UPLOAD_TIMEOUT)
            else:
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                resp = requests.post(
                    url, params=params, data=body,
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    timeout=REQUEST_TIMEOUT,
                )
            result = resp.json()

        if result.get("errcode", 0) != 0:
            raise RuntimeError(f"微信API错误: {result.get('errmsg')} (code: {result.get('errcode')})")
        return result

    def upload_thumb_image(self, image_path: Path) -> str:
        """上传封面图到微信素材库，返回 media_id"""
        if not image_path.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")
        if image_path.stat().st_size > MAX_THUMB_SIZE_BYTES:
            raise ValueError(f"封面图超过 {MAX_THUMB_SIZE_BYTES / 1024 / 1024}MB，请先压缩")

        token = self.token_manager.get_access_token()
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{API_BASE}/cgi-bin/material/add_material",
                params={"access_token": token, "type": "thumb"},
                files={"media": (image_path.name, f)},
                timeout=IMAGE_UPLOAD_TIMEOUT,
            )
        result = resp.json()
        if "media_id" not in result:
            raise RuntimeError(f"封面图上传失败: {result.get('errmsg')}")
        logger.info(f"封面图上传成功: {result['media_id']}")
        return result["media_id"]

    def upload_image_from_url(self, image_url: str) -> str:
        """从 URL 下载图片并上传到微信素材库"""
        from content_processor.processor import download_image
        local_path = download_image(image_url)
        return self.upload_thumb_image(local_path)

    def create_draft(self, title: str, content: str, thumb_media_id: str,
                     author: str = "", digest: str = "",
                     content_source_url: str = "") -> str:
        """
        创建草稿。标题按字节截断，摘要限制 58 字节。
        """
        # 标题截断（中文 3 字节/字，安全截断）
        title_bytes = title.encode("utf-8")
        if len(title_bytes) > TITLE_MAX_BYTES:
            chars, size = [], 0
            for ch in title:
                cs = len(ch.encode("utf-8"))
                if size + cs <= TITLE_MAX_BYTES - 1:
                    chars.append(ch)
                    size += cs
                else:
                    break
            title = "".join(chars) + "..."
            while len(title.encode("utf-8")) > TITLE_MAX_BYTES * 1.5:
                title = title[:-4] + "..."

        # 摘要截断
        if digest and len(digest.encode("utf-8")) > DIGEST_MAX_BYTES:
            digest = digest.encode("utf-8")[:DIGEST_MAX_BYTES - 3].decode("utf-8", errors="ignore") + "..."
        if not digest:
            from bs4 import BeautifulSoup
            import re
            try:
                text = BeautifulSoup(content, "lxml").get_text(separator=" ", strip=True)
                text = re.sub(r"\s+", " ", text).strip()
                digest = text.encode("utf-8")[:55].decode("utf-8", errors="ignore") + "..."
            except Exception:
                digest = "点击查看全文"

        # 如果没有thumb_media_id，尝试从内容中提取第一张图片作为封面
        if not thumb_media_id:
            try:
                from bs4 import BeautifulSoup
                from content_processor.processor import download_image
                soup = BeautifulSoup(content, "lxml")
                first_img = soup.find("img")
                if first_img:
                    img_url = first_img.get("src", "") or first_img.get("data-src", "")
                    if img_url:
                        # 下载图片到本地
                        local_path = download_image(img_url)
                        if local_path and local_path.exists():
                            thumb_media_id = self.upload_thumb_image(local_path)
                            logger.info(f"已使用内容图片作为封面: {local_path}")
            except Exception as e:
                logger.warning(f"提取封面图失败: {e}")

        articles = [{
            "title": title,
            "author": author,
            "digest": digest,
            "content": content,
            "content_source_url": content_source_url,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }]

        result = self._request("/cgi-bin/draft/add", data={"articles": articles})
        logger.info(f"草稿创建成功: {title} (media_id: {result['media_id']})")
        return result["media_id"]

    def get_draft_list(self, offset: int = 0, count: int = 20, no_content: int = 0) -> dict:
        """获取草稿列表"""
        return self._request(
            "/cgi-bin/draft/batchget",
            data={"offset": offset, "count": count, "no_content": no_content},
        )

    def delete_draft(self, media_id: str):
        """删除草稿"""
        self._request("/cgi-bin/draft/delete", data={"media_id": media_id})
        logger.info(f"草稿已删除: {media_id}")

    def upload_image_for_content(self, image_url: str) -> str:
        """上传文章内图片，返回微信 URL"""
        from content_processor.processor import download_image
        local_path = download_image(image_url)
        token = self.token_manager.get_access_token()
        with open(local_path, "rb") as f:
            resp = requests.post(
                f"{API_BASE}/cgi-bin/media/uploadimg",
                params={"access_token": token},
                files={"media": (local_path.name, f)},
                timeout=IMAGE_UPLOAD_TIMEOUT,
            )
        result = resp.json()
        if "url" not in result:
            raise RuntimeError(f"文章图片上传失败: {result.get('errmsg')}")
        logger.info(f"文章图片上传成功")
        return result["url"]

    def replace_content_images(self, html_content: str, max_images: int = MAX_CONTENT_IMAGES) -> str:
        """替换文章 HTML 中的外链图片为微信 URL"""
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse

        soup = BeautifulSoup(html_content, "lxml")
        replaced = 0

        for img in soup.find_all("img"):
            if replaced >= max_images:
                logger.warning(f"图片数量超过 {max_images} 张，停止替换")
                break
            src = img.get("src", "") or img.get("data-src", "")
            if not src:
                continue
            if "mmbiz.qpic.cn" in src or "mmbiz.qlogo.cn" in src or src.startswith("data:"):
                continue
            try:
                wechat_url = self.upload_image_for_content(src)
                img["src"] = wechat_url
                if "data-src" in img.attrs:
                    del img["data-src"]
                replaced += 1
                logger.info(f"图片替换 [{replaced}]: {src[:40]}...")
            except Exception as e:
                logger.error(f"图片替换失败: {src[:40]}... -> {e}")

        if replaced > 0:
            logger.info(f"共替换 {replaced} 张图片")
        return str(soup)


def create_publisher() -> WeChatPublisher:
    """创建发布器实例"""
    return WeChatPublisher()
