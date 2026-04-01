"""主题选择器 — 读写 .theme_selected.json，供 wenyan_render.mjs 使用"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
CONFIG = ROOT / ".theme_selected.json"

def get_theme():
    if not CONFIG.exists():
        return "pie"
    try:
        return json.loads(CONFIG.read_text("utf-8")).get("theme", "pie")
    except:
        return "pie"

def set_theme(theme_id: str):
    CONFIG.write_text(json.dumps({"theme": theme_id, "updated": "now"}, indent=2), "utf-8")
    print(f"Theme set to: {theme_id}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(get_theme())
    elif sys.argv[1] == "get":
        print(get_theme())
    elif sys.argv[1] == "set" and len(sys.argv) >= 3:
        set_theme(sys.argv[2])
    elif sys.argv[1] == "reset":
        set_theme("pie")
    else:
        print("Usage: python theme_config.py [get|set <id>|reset]")
