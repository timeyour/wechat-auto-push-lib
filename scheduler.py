"""
定时调度引擎 - RSS 抓取 + 发布流水线
"""
import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import FETCH_INTERVAL_HOURS, PUBLISH_TIME_RANGE, DEFAULT_AUTHOR
from rss_sources.fetcher import fetch_all_sources, mark_batch_as_published, Article
from content_processor.processor import (
    clean_html, extract_text_summary, build_final_content,
    get_first_image_url, generate_default_cover,
)
from wechat_api.publisher import create_publisher

logger = logging.getLogger(__name__)


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

    articles = fetch_all_sources()
    if not articles:
        logger.info("没有新文章")
        return

    for article in articles:
        cleaned = clean_html(article.content)
        digest = extract_text_summary(cleaned)
        cover = article.cover_url or get_first_image_url(article.content)
        print(f"\n--- {article.title} ---")
        print(f"  来源: {article.source_name} | 标签: {article.tag}")
        print(f"  链接: {article.link}")
        print(f"  摘要: {digest}")
        print(f"  封面: {cover or '(无)'}")
        print(f"  正文长度: {len(cleaned)} 字符")
