"""
定时调度引擎 - RSS 抓取 + 发布流水线
"""
import logging
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import FETCH_INTERVAL_HOURS, PUBLISH_TIME_RANGE, DEFAULT_AUTHOR
from rss_sources.fetcher import fetch_all_sources, mark_batch_as_published, Article
from content_processor.processor import (
    clean_html, extract_text_summary, build_final_content,
    get_first_image_url, generate_default_cover,
)

logger = logging.getLogger(__name__)


def _safe_console_text(text: str) -> str:
    """避免 Windows 默认控制台编码导致试运行输出中断。"""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def process_article(publisher, article: Article) -> bool:
    """处理单篇文章：清洗 → 上传封面 → 替换图片 → 创建草稿"""
    try:
        logger.info(f"处理文章: {article.title}")

        # 1. 清洗内容
        cleaned = clean_html(article.content)

        # 2. 替换外链图片为微信 URL
        try:
            cleaned = publisher.replace_content_images(cleaned)
        except Exception as e:
            logger.warning(f"图片替换出错（文章仍会创建草稿）: {e}")

        # 3. 添加来源和页脚
        final_content = build_final_content(
            cleaned,
            source_url=article.link,
            source_name=article.source_name,
        )

        # 4. 生成摘要
        digest = extract_text_summary(cleaned)

        # 5. 获取/生成封面
        thumb_media_id = ""
        cover_url = article.cover_url or get_first_image_url(article.content)

        if cover_url:
            try:
                thumb_media_id = publisher.upload_image_from_url(cover_url)
            except Exception as e:
                logger.warning(f"封面上传失败: {e}")

        if not thumb_media_id:
            try:
                cover_path = generate_default_cover(article.title)
                thumb_media_id = publisher.upload_thumb_image(cover_path)
                logger.info("使用自动生成封面")
            except Exception as e:
                logger.warning(f"封面生成/上传失败: {e}")

        if not thumb_media_id:
            logger.error(f"文章 [{article.title}] 无封面，跳过")
            return False

        # 6. 创建草稿
        media_id = publisher.create_draft(
            title=article.title,
            content=final_content,
            thumb_media_id=thumb_media_id,
            author=article.author or DEFAULT_AUTHOR,
            digest=digest,
            content_source_url=article.link,
        )
        logger.info(f"草稿创建成功: {article.title} (media_id: {media_id})")
        return True

    except Exception as e:
        logger.error(f"处理失败 [{article.title}]: {e}", exc_info=True)
        return False


def run_once():
    """执行一次抓取 + 发布"""
    logger.info("=" * 60)
    logger.info(f"开始执行: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    now_hour = datetime.now().hour
    if not (PUBLISH_TIME_RANGE[0] <= now_hour < PUBLISH_TIME_RANGE[1]):
        logger.info(f"当前 {now_hour}:00 不在发布时间段 {PUBLISH_TIME_RANGE}，仅抓取")
        articles = fetch_all_sources()
        if articles:
            logger.info(f"抓取到 {len(articles)} 篇（未推草稿）")
        return

    articles = fetch_all_sources()
    if not articles:
        logger.info("没有新文章")
        return

    try:
        from wechat_api.publisher import create_publisher
        publisher = create_publisher()
    except ValueError as e:
        logger.error(f"发布器初始化失败: {e}")
        return

    success, success_list = 0, []
    for article in articles:
        if process_article(publisher, article):
            success += 1
            success_list.append(article)

    if success_list:
        mark_batch_as_published(success_list)

    logger.info("=" * 60)
    logger.info(f"完成: 处理 {len(articles)} 篇，成功 {success} 篇")
    logger.info("请登录 mp.weixin.qq.com 草稿箱手动群发")
    logger.info("=" * 60)


def run_scheduler():
    """启动定时调度器"""
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_once,
        trigger=IntervalTrigger(hours=FETCH_INTERVAL_HOURS),
        id="rss_fetch_and_publish",
        name="RSS抓取并创建草稿",
        replace_existing=True,
    )
    logger.info(f"调度器已启动，每 {FETCH_INTERVAL_HOURS} 小时执行一次")
    logger.info(f"发布时间段: {PUBLISH_TIME_RANGE[0]}:00 - {PUBLISH_TIME_RANGE[1]}:00")
    logger.info("按 Ctrl+C 停止")
    run_once()
    scheduler.start()


def run_dry():
    """试运行 - 只抓取，不发布"""
    logger.info("=" * 60)
    logger.info("试运行模式 - 不创建草稿")
    logger.info("=" * 60)

    result = collect_dry_run_preview()
    if not result["items"]:
        logger.info("没有新文章")
        return

    for item in result["items"]:
        print(_safe_console_text(f"\n--- {item['title']} ---"))
        print(_safe_console_text(f"  来源: {item['source_name']} | 标签: {item['tag']}"))
        print(_safe_console_text(f"  链接: {item['link']}"))
        print(_safe_console_text(f"  摘要: {item['digest']}"))
        print(_safe_console_text(f"  封面: {item['cover'] or '(无)'}"))
        print(_safe_console_text(f"  正文长度: {item['content_length']} 字符"))


def collect_dry_run_preview(limit: int = 8) -> dict:
    """返回页面友好的 dry-run 结果，不创建草稿。"""
    articles = fetch_all_sources()
    items = []

    for article in articles[:limit]:
        cleaned = clean_html(article.content)
        items.append(
            {
                "title": article.title,
                "source_name": article.source_name,
                "tag": article.tag,
                "link": article.link,
                "digest": extract_text_summary(cleaned),
                "cover": article.cover_url or get_first_image_url(article.content),
                "content_length": len(cleaned),
            }
        )

    return {
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_found": len(articles),
        "displayed": len(items),
        "items": items,
    }
