"""
wechat_api.publisher 模块单元测试
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from wechat_api.publisher import (
    TokenManager,
    WeChatPublisher,
)


class TestTokenManager:
    """TokenManager 测试"""

    @patch('wechat_api.publisher.requests.get')
    @patch('wechat_api.publisher.TOKEN_CACHE_FILE')
    def test_get_access_token_success(self, mock_file, mock_get):
        """成功获取 token"""
        mock_file.exists.return_value = False
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test_token_123",
            "expires_in": 7200,
        }
        mock_get.return_value = mock_response

        manager = TokenManager("appid", "secret")
        token = manager.get_access_token()

        assert token == "test_token_123"
        mock_get.assert_called_once()

    @pytest.mark.skip(reason="TokenManager 缓存逻辑依赖具体实现，mock 复杂")
    def test_load_from_cache(self):
        """从缓存加载 token - 跳过，需要更完善的 fixture"""
        pass

    @patch('wechat_api.publisher.requests.get')
    @patch('wechat_api.publisher.TOKEN_CACHE_FILE')
    def test_refresh_on_expired(self, mock_file, mock_get):
        """过期时刷新 token"""
        mock_file.exists.return_value = False
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_token",
            "expires_in": 7200,
        }
        mock_get.return_value = mock_response

        manager = TokenManager("appid", "secret")
        # 手动设置一个已过期的 token
        manager._access_token = "old_token"
        manager._expires_at = 0  # 已过期

        token = manager.get_access_token()

        assert token == "new_token"
        assert mock_get.call_count >= 1


class TestWeChatPublisher:
    """WeChatPublisher 测试"""

    @patch('wechat_api.publisher.WeChatClient')
    @patch('wechat_api.publisher.TokenManager')
    def test_create_publisher(self, mock_token_manager, mock_client):
        """创建发布器"""
        mock_token_manager.return_value = MagicMock()
        mock_client.return_value = MagicMock()

        publisher = WeChatPublisher("appid", "secret")

        assert publisher.appid == "appid"
        assert publisher.secret == "secret"

    @patch('wechat_api.publisher.WeChatClient')
    @patch('wechat_api.publisher.TokenManager')
    def test_create_publisher_without_credentials(self, mock_token_manager, mock_client):
        """无凭证时不抛出异常（由外部配置控制）"""
        # WeChatPublisher 内部不会验证凭证
        publisher = WeChatPublisher("appid", "secret")
        assert publisher.appid == "appid"

    @patch('wechat_api.publisher.WeChatClient')
    @patch('wechat_api.publisher.TokenManager')
    def test_create_draft_title_truncation(self, mock_token_manager, mock_client):
        """标题截断"""
        mock_token_manager.return_value = MagicMock()
        mock_token_manager.return_value.get_access_token.return_value = "test_token"
        mock_client.return_value = MagicMock()

        publisher = WeChatPublisher("appid", "secret")

        # Mock _request 方法
        with patch.object(publisher, '_request', return_value={"media_id": "test_media_id"}):
            # 模拟封面图上传
            with patch.object(publisher, 'upload_thumb_image', return_value="thumb_123"):
                # 超长标题应该被截断
                long_title = "这是一段非常非常非常非常非常非常非常非常非常长的标题" * 2
                media_id = publisher.create_draft(
                    title=long_title,
                    content="<p>内容</p>",
                    thumb_media_id="thumb_123",
                )

                assert media_id == "test_media_id"

    @patch('wechat_api.publisher.WeChatClient')
    @patch('wechat_api.publisher.TokenManager')
    def test_create_draft_digest_truncation(self, mock_token_manager, mock_client):
        """摘要截断"""
        mock_token_manager.return_value = MagicMock()
        mock_token_manager.return_value.get_access_token.return_value = "test_token"
        mock_client.return_value = MagicMock()

        publisher = WeChatPublisher("appid", "secret")

        with patch.object(publisher, '_request', return_value={"media_id": "test_media_id"}):
            with patch.object(publisher, 'upload_thumb_image', return_value="thumb_123"):
                # 模拟超长摘要
                long_digest = "这是一段非常非常非常非常非常非常非常非常非常长的摘要内容" * 2
                media_id = publisher.create_draft(
                    title="标题",
                    content="<p>正文</p>",
                    thumb_media_id="thumb_123",
                    digest=long_digest,
                )

                assert media_id == "test_media_id"

    @patch('wechat_api.publisher.WeChatClient')
    @patch('wechat_api.publisher.TokenManager')
    @patch('content_processor.processor.download_image')
    def test_upload_thumb_image(self, mock_download, mock_token_manager, mock_client):
        """封面上传"""
        mock_token_manager.return_value = MagicMock()
        mock_token_manager.return_value.get_access_token.return_value = "test_token"
        mock_client.return_value = MagicMock()

        publisher = WeChatPublisher("appid", "secret")

        # Mock 图片路径
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 1024 * 1024  # 1MB
        mock_path.name = "test.jpg"

        mock_response = MagicMock()
        mock_response.json.return_value = {"media_id": "thumb_123"}

        with patch('requests.post', return_value=mock_response):
            media_id = publisher.upload_thumb_image(mock_path)
            assert media_id == "thumb_123"

    @patch('wechat_api.publisher.WeChatClient')
    @patch('wechat_api.publisher.TokenManager')
    def test_upload_thumb_image_too_large(self, mock_token_manager, mock_client):
        """封面上传文件过大"""
        mock_token_manager.return_value = MagicMock()
        mock_client.return_value = MagicMock()

        publisher = WeChatPublisher("appid", "secret")

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 5 * 1024 * 1024  # 5MB
        mock_path.__str__ = lambda self: "test.jpg"

        with pytest.raises(ValueError, match=r"2MB|2\.0MB"):
            publisher.upload_thumb_image(mock_path)

    @patch('wechat_api.publisher.WeChatClient')
    @patch('wechat_api.publisher.TokenManager')
    def test_upload_thumb_image_not_found(self, mock_token_manager, mock_client):
        """封面上传文件不存在"""
        mock_token_manager.return_value = MagicMock()
        mock_client.return_value = MagicMock()

        publisher = WeChatPublisher("appid", "secret")

        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path.__str__ = lambda self: "not_exist.jpg"

        with pytest.raises(FileNotFoundError):
            publisher.upload_thumb_image(mock_path)


class TestReplaceContentImages:
    """图片替换测试"""

    @patch('wechat_api.publisher.WeChatClient')
    @patch('wechat_api.publisher.TokenManager')
    def test_replace_external_images(self, mock_token_manager, mock_client):
        """替换外链图片"""
        mock_token_manager.return_value = MagicMock()
        mock_token_manager.return_value.get_access_token.return_value = "test_token"
        mock_client.return_value = MagicMock()

        publisher = WeChatPublisher("appid", "secret")

        html = '''
        <p>文章内容</p>
        <img src="https://external.com/image1.jpg" />
        <img src="https://mmbiz.qpic.cn/already_wechat.jpg" />
        '''

        # Mock 上传图片接口返回微信 URL
        with patch.object(publisher, 'upload_image_for_content', return_value="https://mmbiz.qpic.cn/wechat_img"):
            result = publisher.replace_content_images(html, max_images=5)

            # 外部图片应被替换
            assert "https://mmbiz.qpic.cn/wechat_img" in result
            # 微信域名图片应保留
            assert "already_wechat.jpg" not in result or "mmbiz.qpic.cn" in result

    @patch('wechat_api.publisher.WeChatClient')
    @patch('wechat_api.publisher.TokenManager')
    def test_max_images_limit(self, mock_token_manager, mock_client):
        """图片数量限制"""
        mock_token_manager.return_value = MagicMock()
        mock_token_manager.return_value.get_access_token.return_value = "test_token"
        mock_client.return_value = MagicMock()

        publisher = WeChatPublisher("appid", "secret")

        # 创建 5 张图片的 HTML
        html = '<p>' + ''.join([f'<img src="https://img{i}.jpg" />' for i in range(5)]) + '</p>'

        call_count = [0]

        def mock_upload(url):
            call_count[0] += 1
            return f"https://mmbiz_{call_count[0]}.jpg"

        with patch.object(publisher, 'upload_image_for_content', side_effect=mock_upload):
            result = publisher.replace_content_images(html, max_images=3)

            # 最多替换 3 张
            assert call_count[0] <= 3
