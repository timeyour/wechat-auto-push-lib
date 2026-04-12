"""主题选择器 — 读写 .theme_selected.json，供本地面板和 wenyan_render.mjs 使用。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from theme_library import DEFAULT_THEME

ROOT = Path(__file__).parent.resolve()
CONFIG = ROOT / ".theme_selected.json"


def get_theme() -> str:
    if not CONFIG.exists():
        return DEFAULT_THEME
    try:
        return json.loads(CONFIG.read_text("utf-8")).get("theme", DEFAULT_THEME)
    except Exception:
        return DEFAULT_THEME


def set_theme(theme_id: str) -> None:
    CONFIG.write_text(
        json.dumps({"theme": theme_id, "updated": "now"}, indent=2, ensure_ascii=False),
        "utf-8",
    )


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(get_theme())
    elif sys.argv[1] == "get":
        print(get_theme())
    elif sys.argv[1] == "set" and len(sys.argv) >= 3:
        set_theme(sys.argv[2])
        print(f"Theme set to: {sys.argv[2]}")
    elif sys.argv[1] == "reset":
        set_theme(DEFAULT_THEME)
        print(f"Theme set to: {DEFAULT_THEME}")
    else:
        print("Usage: python theme_config.py [get|set <id>|reset]")
