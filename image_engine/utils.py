# -*- coding: utf-8 -*-
import logging
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).parent.parent
ENV_FILE = APP_DIR / ".env"
OUT_DIR = APP_DIR / "generated-images"
OUT_DIR.mkdir(exist_ok=True)

# 日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("img_fallback")

def load_env():
    """从 .env 加载环境变量"""
    if not ENV_FILE.exists():
        logger.warning(f".env 未找到: {ENV_FILE}")
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()
