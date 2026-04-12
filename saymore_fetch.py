#!/usr/bin/env python3
"""
saymore-fetch — Saymore.app 精选内容抓取工具

⚠️  此文件为计划实现占位，尚未接入真实 Saymore API。
如需使用，请参考 skills/saymore-fetch/SKILL.md 的完整设计文档。

计划功能：
- 列出所有已订阅的 Collection
- 按 Collection ID 抓取最新条目（分页）
- 按 24h 活跃度排序抓取 Top Collection
- 预设快捷键：github / builders / polymarket / musk 等
"""

from typing import Any

API_KEY = ""  # 尚未配置
PRESETS = {}


def list_subscriptions() -> list[dict[str, Any]]:
    raise NotImplementedError("saymore_fetch: 待接入 Saymore API")


def fetch_collection(cid: int, limit: int = 10) -> list[dict[str, Any]]:
    raise NotImplementedError("saymore_fetch: 待接入 Saymore API")


def fetch_top(limit: int = 3) -> list[dict[str, Any]]:
    raise NotImplementedError("saymore_fetch: 待接入 Saymore API")


if __name__ == "__main__":
    import sys

    print("saymore_fetch: 此工具尚未实现")
    print("参考 skills/saymore-fetch/SKILL.md 了解计划功能")
    sys.exit(1)
