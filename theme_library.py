"""Theme library helpers for builtin and custom Wenyan presets."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Dict, List

from bs4 import BeautifulSoup

from config import DATA_DIR

DEFAULT_THEME = "pie"
THEME_LIBRARY_FILE = DATA_DIR / "theme_library.json"

BUILTIN_THEMES = [
    {"id": "default", "name": "Default", "desc": "经典蓝灰 · 简洁长文阅读"},
    {"id": "orangeheart", "name": "OrangeHeart", "desc": "暖橙色调 · 优雅活力"},
    {"id": "rainbow", "name": "Rainbow", "desc": "彩虹色 · 清新活泼"},
    {"id": "lapis", "name": "Lapis", "desc": "冷蓝色调 · 极简清爽"},
    {"id": "pie", "name": "Pie", "desc": "少数派风格 · 现代锐利"},
    {"id": "maize", "name": "Maize", "desc": "浅黄色调 · 柔和精致"},
    {"id": "purple", "name": "Purple", "desc": "淡紫色调 · 干净极简"},
    {"id": "phycat", "name": "PhyCat", "desc": "薄荷绿 · 结构清晰"},
]

KIND_LABELS = {
    "builtin": "内置",
    "custom": "自定义",
    "copycat": "仿写",
}

DEFAULT_STYLE_PROFILE = {
    "title_color": "",
    "body_color": "",
    "accent_color": "",
    "quote_background": "",
    "heading_weight": "800",
}


def list_builtin_themes() -> List[Dict[str, object]]:
    return [
        {
            **theme,
            "kind": "builtin",
            "kind_label": KIND_LABELS["builtin"],
            "base_theme": theme["id"],
            "inspiration": "",
            "style_profile": dict(DEFAULT_STYLE_PROFILE),
        }
        for theme in BUILTIN_THEMES
    ]


def list_all_themes() -> List[Dict[str, object]]:
    return list_builtin_themes() + load_custom_themes()


def load_custom_themes() -> List[Dict[str, object]]:
    if not THEME_LIBRARY_FILE.exists():
        return []

    try:
        payload = json.loads(THEME_LIBRARY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    raw_themes = payload if isinstance(payload, list) else payload.get("custom_themes", [])
    themes: List[Dict[str, object]] = []
    for item in raw_themes:
        normalized = _normalize_custom_theme(item)
        if normalized:
            themes.append(normalized)
    return themes


def get_theme_spec(theme_id: str | None) -> Dict[str, object]:
    for theme in list_all_themes():
        if theme["id"] == theme_id:
            return theme
    return next(theme for theme in list_builtin_themes() if theme["id"] == DEFAULT_THEME)


def create_custom_theme(
    *,
    name: str,
    base_theme: str,
    description: str = "",
    inspiration: str = "",
    kind: str = "custom",
    style_profile: Dict[str, str] | None = None,
) -> Dict[str, object]:
    style_profile = {**DEFAULT_STYLE_PROFILE, **(style_profile or {})}
    theme_id = _build_theme_id(name)
    normalized_kind = kind if kind in ("custom", "copycat") else "custom"
    return {
        "id": theme_id,
        "name": name.strip(),
        "desc": description.strip() or "基于现有主题再做一层你的风格修正",
        "kind": normalized_kind,
        "kind_label": KIND_LABELS[normalized_kind],
        "base_theme": base_theme if base_theme in builtin_theme_ids() else DEFAULT_THEME,
        "inspiration": inspiration.strip(),
        "style_profile": style_profile,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def save_custom_theme(theme: Dict[str, object]) -> None:
    themes = [item for item in load_custom_themes() if item["id"] != theme["id"]]
    themes.append(_normalize_custom_theme(theme))
    _write_custom_themes(themes)


def delete_custom_theme(theme_id: str) -> None:
    themes = [item for item in load_custom_themes() if item["id"] != theme_id]
    _write_custom_themes(themes)


def builtin_theme_ids() -> set[str]:
    return {theme["id"] for theme in BUILTIN_THEMES}


def apply_theme_profile(html: str, theme_spec: Dict[str, object]) -> str:
    style_profile = {**DEFAULT_STYLE_PROFILE, **(theme_spec.get("style_profile") or {})}
    if not any(style_profile.values()):
        return html

    soup = BeautifulSoup(html, "lxml")
    root = soup.body if soup.body else soup

    heading_style = _build_inline_style(
        color=style_profile.get("title_color", ""),
        font_weight=style_profile.get("heading_weight", ""),
    )
    if heading_style:
        for tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            for tag in root.find_all(tag_name):
                _append_inline_style(tag, heading_style)

    body_style = _build_inline_style(color=style_profile.get("body_color", ""))
    if body_style:
        for tag_name in ("p", "li"):
            for tag in root.find_all(tag_name):
                _append_inline_style(tag, body_style)

    accent_style = _build_inline_style(color=style_profile.get("accent_color", ""))
    if accent_style:
        for tag_name in ("strong", "a"):
            for tag in root.find_all(tag_name):
                _append_inline_style(tag, accent_style)

    quote_style = _build_quote_style(style_profile)
    if quote_style:
        for tag in root.find_all("blockquote"):
            _append_inline_style(tag, quote_style)

    return _extract_fragment_html(soup)


def _normalize_custom_theme(raw: Dict[str, object] | None) -> Dict[str, object] | None:
    if not isinstance(raw, dict) or not raw.get("id") or not raw.get("name"):
        return None
    kind = raw.get("kind", "custom")
    kind = kind if kind in ("custom", "copycat") else "custom"
    return {
        "id": str(raw["id"]),
        "name": str(raw["name"]),
        "desc": str(raw.get("desc", "") or "基于现有主题再做一层你的风格修正"),
        "kind": kind,
        "kind_label": KIND_LABELS[kind],
        "base_theme": str(raw.get("base_theme", DEFAULT_THEME))
        if str(raw.get("base_theme", DEFAULT_THEME)) in builtin_theme_ids()
        else DEFAULT_THEME,
        "inspiration": str(raw.get("inspiration", "")),
        "style_profile": {
            **DEFAULT_STYLE_PROFILE,
            **(raw.get("style_profile") or {}),
        },
        "created_at": str(raw.get("created_at", "")),
    }


def _write_custom_themes(themes: List[Dict[str, object]]) -> None:
    if themes:
        THEME_LIBRARY_FILE.parent.mkdir(exist_ok=True)
        payload = {
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "custom_themes": themes,
        }
        THEME_LIBRARY_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    elif THEME_LIBRARY_FILE.exists():
        THEME_LIBRARY_FILE.unlink()


def _build_theme_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        slug = datetime.now().strftime("%Y%m%d%H%M%S")
    theme_id = f"custom-{slug}"
    existing = {theme["id"] for theme in load_custom_themes()}
    suffix = 2
    unique_id = theme_id
    while unique_id in existing:
        unique_id = f"{theme_id}-{suffix}"
        suffix += 1
    return unique_id


def _build_inline_style(*, color: str = "", font_weight: str = "") -> str:
    styles = []
    if color:
        styles.append(f"color: {color} !important;")
    if font_weight:
        styles.append(f"font-weight: {font_weight} !important;")
    return " ".join(styles)


def _build_quote_style(style_profile: Dict[str, str]) -> str:
    styles = []
    accent_color = style_profile.get("accent_color", "")
    body_color = style_profile.get("body_color", "")
    quote_background = style_profile.get("quote_background", "")

    if quote_background:
        styles.append(f"background: {quote_background} !important;")
    if accent_color:
        styles.append(f"border-left: 4px solid {accent_color} !important;")
    if body_color:
        styles.append(f"color: {body_color} !important;")
    if styles:
        styles.append("padding: 14px 18px !important;")
        styles.append("border-radius: 16px !important;")
    return " ".join(styles)


def _append_inline_style(tag, style: str) -> None:
    existing = tag.get("style", "").strip()
    if existing and not existing.endswith(";"):
        existing += ";"
    tag["style"] = f"{existing} {style}".strip()


def _extract_fragment_html(soup: BeautifulSoup) -> str:
    if soup.body:
        return "".join(str(child) for child in soup.body.contents)
    return "".join(str(child) for child in soup.contents)
