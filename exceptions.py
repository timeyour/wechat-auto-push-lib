"""
微信公众号自动推送异常定义

异常层次结构：
    WeChatPushError (基类)
    ├── TokenError
    │   ├── TokenExpiredError
    │   └── TokenFetchError
    ├── APIError
    │   ├── DraftCreationError
    │   ├── ImageUploadError
    │   └── MaterialError
    └── ContentError
        ├── ContentFetchError
        └── ContentParseError
"""
from __future__ import annotations


class WeChatPushError(Exception):
    """微信公众号推送基础异常"""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.message = message
        self.original_error = original_error

    def __str__(self) -> str:
        if self.original_error:
            return f"{self.message} (原始错误: {self.original_error})"
        return self.message


# === Token 相关异常 ===

class TokenError(WeChatPushError):
    """Token 相关基础异常"""
    pass


class TokenExpiredError(TokenError):
    """Access Token 已过期"""
    pass


class TokenFetchError(TokenError):
    """获取 Access Token 失败"""
    pass


# === API 相关异常 ===

class APIError(WeChatPushError):
    """微信 API 调用基础异常"""

    def __init__(self, message: str, errcode: int = 0, errmsg: str = ""):
        super().__init__(message)
        self.errcode = errcode
        self.errmsg = errmsg

    def __str__(self) -> str:
        return f"{self.message} (errcode={self.errcode}, errmsg={self.errmsg})"


class DraftCreationError(APIError):
    """创建草稿失败"""
    pass


class ImageUploadError(APIError):
    """图片上传失败"""
    pass


class MaterialError(APIError):
    """素材操作失败"""
    pass


# === 内容相关异常 ===

class ContentError(WeChatPushError):
    """内容处理基础异常"""
    pass


class ContentFetchError(ContentError):
    """内容抓取失败（如网络错误、超时）"""

    def __init__(self, url: str, message: str, original_error: Exception | None = None):
        super().__init__(f"抓取内容失败 [{url}]: {message}", original_error)
        self.url = url


class ContentParseError(ContentError):
    """内容解析失败（如 HTML 格式错误、正文提取失败）"""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(f"解析内容失败: {message}", original_error)


# === RSS 相关异常 ===

class RSSError(WeChatPushError):
    """RSS 相关基础异常"""
    pass


class RSSParseError(RSSError):
    """RSS 解析失败"""

    def __init__(self, source_name: str, message: str, original_error: Exception | None = None):
        super().__init__(f"RSS 解析失败 [{source_name}]: {message}", original_error)
        self.source_name = source_name


# === 配置相关异常 ===

class ConfigError(WeChatPushError):
    """配置相关异常"""
    pass


class MissingConfigError(ConfigError):
    """缺少必要配置项"""

    def __init__(self, config_name: str):
        super().__init__(f"缺少必要配置项: {config_name}")
        self.config_name = config_name
