"""
微信公众号自动推送 - 默认配置

公开仓库自带 config.py，开箱即可读取 .env。
如果需要保留个人覆盖项，请新建 config.local.py 或直接修改环境变量。
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
    {"name": "36氪", "url": "https://36kr.com/feed", "tag": "AI/科技"},
    {"name": "量子位", "url": "https://www.qbitai.com/rss", "tag": "AI"},
    {"name": "机器之心", "url": "https://www.jiqizhixin.com/rss", "tag": "AI"},
    {"name": "少数派", "url": "https://sspai.com/feed", "tag": "效率工具"},
    {"name": "虎嗅", "url": "https://www.huxiu.com/rss/0.xml", "tag": "商业"},
    {"name": "InfoQ中文", "url": "https://www.infoq.cn/feed", "tag": "技术"},
    {"name": "阮一峰", "url": "https://www.ruanyifeng.com/blog/atom.xml", "tag": "技术"},
]

# === 内容处理配置 ===
MAX_ARTICLES_PER_SOURCE = 3    # 每个源每次最多抓取几篇
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

# === 魔法常量（统一管理） ===

# 微信 API 相关
API_BASE = "https://api.weixin.qq.com"
TOKEN_CACHE_FILE = DATA_DIR / "token_cache.json"
TOKEN_REFRESH_AHEAD_SECONDS = 60  # 提前多少秒刷新 token
REQUEST_TIMEOUT = 30               # API 请求超时（秒）
IMAGE_UPLOAD_TIMEOUT = 60          # 图片上传超时（秒）

# 封面图相关
MAX_THUMB_SIZE_BYTES = 2 * 1024 * 1024      # 封面图最大 2MB
COVER_DIMENSIONS = (900, 383)                 # 封面图尺寸（2.35:1 比例）
COVER_QUALITY = 85                            # JPEG 压缩质量
COVER_CACHE_MAX_SIZE = 1.8 * 1024 * 1024     # 自动压缩阈值 1.8MB

# 标题相关
TITLE_MAX_BYTES = 28        # 标题最大字节数
TITLE_DISPLAY_LENGTH = 18   # 封面显示的标题最大字符数

# 内容过滤
MIN_CONTENT_LENGTH = 100    # 正文最小字符数（低于此值不处理）
CHINESE_THRESHOLD = 0.3     # 中文内容占比阈值

# 图片处理
MAX_CONTENT_IMAGES = 10     # 单篇文章最多替换图片数

# 试运行预览
DRY_RUN_PREVIEW_LIMIT = 8   # 试运行最多预览文章数
