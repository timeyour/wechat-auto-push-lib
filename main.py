#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号自动推送工具入口

使用方式：
  python main.py           # 启动定时调度
  python main.py --once    # 立即执行一次
  python main.py --dry     # 试运行，只抓取不发草稿
  python main.py --list    # 查看草稿箱
  python main.py --web     # 打开本地浏览器面板
  python main.py -v        # 详细日志
"""
import argparse
import logging
import sys

from config import WECHAT_APPID, WECHAT_APPSECRET


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="微信公众号自动推送工具")
    parser.add_argument("--once", action="store_true", help="立即执行一次")
    parser.add_argument("--dry", action="store_true", help="试运行，只抓取不发草稿")
    parser.add_argument("--list", action="store_true", help="查看草稿箱")
    parser.add_argument("--web", action="store_true", help="打开本地浏览器面板")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志")
    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.web:
        from local_panel import run_local_panel

        run_local_panel()
        return

    if not WECHAT_APPID or not WECHAT_APPSECRET:
        logger = logging.getLogger(__name__)
        if not args.dry:
            logger.error("未设置 WECHAT_APPID 或 WECHAT_APPSECRET")
            logger.error("请在 .env 中配置微信公众号凭证，或按需修改 config.py")
            sys.exit(1)

    if args.dry:
        from scheduler import run_dry

        run_dry()
    elif args.list:
        from wechat_api.publisher import create_publisher

        publisher = create_publisher()
        drafts = publisher.get_draft_list(count=10, no_content=1)
        items = drafts.get("item_count", 0)
        logger = logging.getLogger(__name__)
        logger.info("草稿箱共 %s 篇草稿", items)
        for index, draft in enumerate(drafts.get("item", []), 1):
            articles = draft.get("content", {}).get("news_item", [])
            for article in articles:
                logger.info(
                    "  %s. %s | media_id: %s",
                    index,
                    article.get("title", "无标题"),
                    draft.get("media_id", ""),
                )
    elif args.once:
        from scheduler import run_once

        run_once()
    else:
        from scheduler import run_scheduler

        try:
            run_scheduler()
        except KeyboardInterrupt:
            logging.info("调度器已停止")


if __name__ == "__main__":
    main()
