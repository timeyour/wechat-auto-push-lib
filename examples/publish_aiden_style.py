"""
符合Aiden AI Life Mode公众号风格的发布脚本
排版特点：
- 极简风格，无花哨颜色
- 绿色(#07c160)作为强调色
- 清晰的编号章节结构
"""
from pathlib import Path

import markdown
import requests
from bs4 import BeautifulSoup

# 导入项目模块
from wechat_api.publisher import WeChatPublisher


def upload_local_image(publisher: WeChatPublisher, local_path: Path) -> str:
    """上传本地图片到微信，返回URL"""
    token = publisher.token_manager.get_access_token()
    with open(local_path, 'rb') as f:
        resp = requests.post(
            "https://api.weixin.qq.com/cgi-bin/media/uploadimg",
            params={"access_token": token},
            files={"media": (local_path.name, f)},
            timeout=60,
        )
    result = resp.json()
    if "url" not in result:
        raise RuntimeError(f"图片上传失败: {result.get('errmsg')}")
    return result["url"]


def build_aiden_style_content(md_content: str, images_dir: Path = None) -> str:
    """
    构建符合Aiden公众号风格的HTML内容

    排版规范：
    - 主标题：26px，Bold，#333333，居中
    - 标签：绿色#07c160，小号，居中
    - 章节标题：18px，Bold，#333，带绿色左边框
    - 正文：16px，行高1.8，#333333
    - 引用块：灰色背景+绿色左边框
    - 表格：简洁边框样式
    """
    # 渲染Markdown
    raw_html = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'toc'],
        extension_configs={
            'toc': {'title': '目录'}
        }
    )
    soup = BeautifulSoup(raw_html, 'lxml')

    # 构建HTML头部样式
    html_style = """
    <style>
        .article-header {
            text-align: center;
            padding: 30px 20px 20px;
        }
        .article-tag {
            color: #07c160;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 2px;
            margin-bottom: 15px;
        }
        .article-title {
            color: #333333;
            font-size: 26px;
            font-weight: 700;
            line-height: 1.4;
            margin: 0 0 20px 0;
        }
        .article-divider {
            width: 60px;
            height: 3px;
            background: #07c160;
            margin: 20px auto;
        }
        .article-content {
            padding: 0 16px;
        }
        .article-content p {
            font-size: 16px;
            line-height: 1.8;
            color: #333333;
            margin: 0 0 20px 0;
            text-align: justify;
        }
        .article-content h2 {
            font-size: 19px;
            font-weight: 700;
            color: #333333;
            margin: 30px 0 15px 0;
            padding-left: 12px;
            border-left: 4px solid #07c160;
        }
        .article-content h3 {
            font-size: 17px;
            font-weight: 700;
            color: #333333;
            margin: 25px 0 12px 0;
        }
        .article-content h4 {
            font-size: 16px;
            font-weight: 700;
            color: #555555;
            margin: 20px 0 10px 0;
        }
        .article-content blockquote {
            margin: 20px 0;
            padding: 15px 18px;
            background-color: #f7f7f7;
            border-left: 4px solid #07c160;
            border-radius: 0 6px 6px 0;
        }
        .article-content blockquote p {
            font-size: 15px;
            color: #555555;
            margin: 0;
            line-height: 1.7;
        }
        .article-content ul, .article-content ol {
            margin: 15px 0 20px 0;
            padding-left: 25px;
        }
        .article-content li {
            font-size: 16px;
            line-height: 1.8;
            color: #333333;
            margin-bottom: 8px;
        }
        .article-content strong {
            font-weight: 700;
            color: #000000;
        }
        .article-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }
        .article-content table th {
            background: #f7f7f7;
            font-weight: 700;
            padding: 12px 10px;
            text-align: left;
            border: 1px solid #e5e5e5;
        }
        .article-content table td {
            padding: 10px;
            border: 1px solid #e5e5e5;
            vertical-align: top;
        }
        .article-content img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 20px auto;
            border-radius: 6px;
        }
        .article-content hr {
            border: none;
            border-top: 1px solid #e5e5e5;
            margin: 30px 0;
        }
        .article-content code {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 14px;
        }
        .article-content pre {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 15px 0;
        }
        .article-footer {
            margin-top: 40px;
            padding: 20px 16px;
            background: #fafafa;
            border-radius: 8px;
        }
        .article-footer p {
            font-size: 14px;
            color: #888888;
            margin: 5px 0;
            text-align: center;
        }
        .highlight-green {
            color: #07c160;
            font-weight: 600;
        }
    </style>
    """

    # 构建封面区域
    cover_html = """
    <div class="article-header">
        <div class="article-tag">有用AI · 2026趋势</div>
        <h1 class="article-title">{title}</h1>
        <div class="article-divider"></div>
    </div>
    """

    # 提取标题
    title_match = md_content.split('\n')[0]
    if title_match.startswith('# '):
        title = title_match[2:].strip()
    else:
        title = "AI三国杀"

    # 构建页脚
    footer_html = """
    <div class="article-footer">
        <p>---</p>
        <p>本文内容来源于公开信息整理，观点仅供参考。</p>
        <p>作者：Aiden | AI Life Mode</p>
        <p>本文部分内容由AI辅助创作</p>
    </div>
    """

    # 组装完整HTML
    content_html = str(soup)
    final_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {html_style}
    </head>
    <body>
        {cover_html.format(title=title)}
        <div class="article-content">
            {content_html}
        </div>
        {footer_html}
    </body>
    </html>
    """

    return final_html


def upload_content_images(html_content: str, publisher, images_dir: Path = None) -> str:
    """
    上传HTML内容中的图片并替换URL

    Args:
        html_content: HTML内容
        publisher: 微信发布器实例
        images_dir: 本地图片目录

    Returns:
        替换图片URL后的HTML内容
    """
    soup = BeautifulSoup(html_content, 'lxml')
    updated_count = 0

    for img in soup.find_all('img'):
        src = img.get('src', '')
        if not src:
            continue

        # 处理本地图片
        if src.startswith('/') or src.startswith('.'):
            local_path = Path(src)
            if not local_path.is_absolute() and images_dir:
                local_path = images_dir / local_path

            if local_path.exists():
                try:
                    uploaded_url = upload_local_image(publisher, local_path)
                    img['src'] = uploaded_url
                    updated_count += 1
                except Exception as e:
                    print(f"图片上传失败: {local_path}, 错误: {e}")

        # 处理网络图片（直接使用）
        elif src.startswith('http'):
            updated_count += 1

    print(f"图片处理完成: {updated_count} 张图片")
    return str(soup)


def publish_article_aiden_style(
    article_path: str,
    author_name: str = "Aiden",
    need_cover: bool = True,
    cover_path: str = None
):
    """
    使用Aiden公众号风格发布文章

    Args:
        article_path: 文章Markdown文件路径
        author_name: 作者名称
        need_cover: 是否需要封面
        cover_path: 封面图片路径（可选）
    """
    # 读取文章
    article_file = Path(article_path)
    if not article_file.exists():
        raise FileNotFoundError(f"文章文件不存在: {article_path}")

    md_content = article_file.read_text(encoding='utf-8')

    # 提取标题
    title = md_content.split('\n')[0]
    if title.startswith('# '):
        title = title[2:].strip()

    print(f"📝 文章标题: {title}")

    # 构建样式内容
    html_content = build_aiden_style_content(md_content)

    # 创建发布器
    publisher = WeChatPublisher()

    # 上传图片
    images_dir = article_file.parent.parent / 'images'
    html_content = upload_content_images(html_content, publisher, images_dir)

    # 处理封面
    thumb_media_id = None
    if need_cover:
        if cover_path and Path(cover_path).exists():
            try:
                thumb_media_id = publisher.upload_thumb_image(Path(cover_path))
                print(f"✅ 封面上传成功: {thumb_media_id}")
            except Exception as e:
                print(f"⚠️ 封面上传失败: {e}, 将不使用封面")
        else:
            print("⚠️ 未提供封面图或封面不存在，将不使用封面")

    # 创建草稿
    draft_id = publisher.create_draft(
        title=title,
        author=author_name,
        content=html_content,
        digest=md_content[:200] + "...",
        thumb_media_id=thumb_media_id
    )

    if draft_id:
        print("✅ 草稿创建成功!")
        print(f"📋 草稿ID: {draft_id}")
        return draft_id
    else:
        print("❌ 草稿创建失败")
        return None


# 默认封面图路径
DEFAULT_COVER = Path(__file__).parent.parent / 'data' / 'covers' / 'cover_bg.jpg'


if __name__ == "__main__":
    import sys

    # 默认文章路径
    article_path = Path(__file__).parent.parent / 'data' / 'articles' / 'article_20260412.md'

    if len(sys.argv) > 1:
        article_path = sys.argv[1]

    print("=" * 50)
    print("Aiden公众号风格发布")
    print("=" * 50)

    draft_id = publish_article_aiden_style(
        article_path=str(article_path),
        author_name="Aiden",
        need_cover=True,
        cover_path=str(DEFAULT_COVER)
    )

    if draft_id:
        print("\n🎉 发布成功! 请前往微信公众号后台查看草稿")
