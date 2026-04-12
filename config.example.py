"""
微信公众号自动推送 - 配置示例

仓库内已自带可直接读取 .env 的 config.py。
这个文件只作为字段说明和自定义参考，不再是启动前置步骤。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# === 项目路径 ===
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

PUBLISHED_FILE = DATA_DIR / "published_urls.json"  # 已发布URL记录（去重用）
COVER_CACHE = DATA_DIR / "covers"                  # 封面图片缓存
COVER_CACHE.mkdir(exist_ok=True)

# === 微信公众号配置 ===
# 在 mp.weixin.qq.com → 设置 → 基本配置 中获取
WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_APPSECRET = os.getenv("WECHAT_APPSECRET", "")

# === RSS 源配置 ===
# 可自行增删，每个源每次最多抓取 MAX_ARTICLES_PER_SOURCE 篇
RSS_SOURCES = [
    {"name": "36氪",       "url": "https://36kr.com/feed",          "tag": "AI/科技"},
    {"name": "量子位",     "url": "https://www.qbitai.com/rss",     "tag": "AI"},
    {"name": "机器之心",   "url": "https://www.jiqizhixin.com/rss", "tag": "AI"},
    {"name": "少数派",     "url": "https://sspai.com/feed",         "tag": "效率工具"},
    {"name": "虎嗅",       "url": "https://www.huxiu.com/rss/0.xml","tag": "商业"},
    {"name": "InfoQ中文",  "url": "https://www.infoq.cn/feed",      "tag": "技术"},
    {"name": "阮一峰",     "url": "https://www.ruanyifeng.com/blog/atom.xml", "tag": "技术"},
]

# === 内容处理配置 ===
MAX_ARTICLES_PER_SOURCE = 3   # 每个源每次最多抓取几篇
DIGEST_MAX_BYTES = 58          # 摘要最大字节数（未认证订阅号限制约62字节）
AUTO_DOWNLOAD_COVER = True     # 自动下载文章第一张图作为封面

# 默认封面（文章无图片时使用，需先上传到微信素材库获取 media_id）
DEFAULT_COVER_MEDIA_ID = os.getenv("DEFAULT_COVER_MEDIA_ID", "")

# === 发布配置 ===
DEFAULT_AUTHOR = os.getenv("DEFAULT_AUTHOR", "")   # 文章作者，留空则不设置

# 文章底部版权声明（HTML），留空则不添加
FOOTER_HTML = os.getenv("FOOTER_HTML", """
<section style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 14px; text-align: center;">
    <p>本文内容来源于互联网，版权归原作者所有。</p>
    <p>关注公众号，获取更多精选内容。</p>
</section>
""")

# === 调度配置 ===
FETCH_INTERVAL_HOURS = int(os.getenv("FETCH_INTERVAL_HOURS", "6"))  # 抓取间隔（小时）
PUBLISH_TIME_RANGE = (8, 22)   # 允许推草稿的时间段（24小时制，8:00-22:00）
