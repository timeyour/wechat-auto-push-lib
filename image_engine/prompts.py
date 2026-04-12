# -*- coding: utf-8 -*-

# 封面风格模板（升级版：融入“好用”进化规则，适配公众号主视觉）
# 进化点：
#   1. 视觉钩子 (Visual Hook)：背景极简，配色严控 3 种以内。
#   2. 文字安全区：主体元素避开中心区域，为标题留出 20% 高度的展示空间。
#   3. 电影感比例：强制 --ar 2.35:1 (900x383)。

COVER_STYLES = {
    "tech": {
        "subject": "AI, future technology, minimalist abstract concept",
        "env": "clean gradient background, deep blue and dark cyan #0a1628 to #1a3a5c, subtle digital grid, holographic lines",
        "lighting": "soft futuristic neon glow, cold blue light, minimalist lighting",
        "composition": "center-aligned empty space for text, minimalist, rule of thirds, wide shot, --ar 2.35:1",
        "color": "limited color palette: deep blue, cyan, and subtle white, maximum 3 colors",
        "quality": "4k resolution, high quality, professional graphic design, no text, no watermark",
        "prompt_template": "{subject}, {env}, {lighting}, {composition}, {color}, {quality}",
    },
    "warm": {
        "subject": "lifestyle, warm and cozy, soft abstract shapes",
        "env": "clean minimalist background, soft bokeh, warm Morandi tones, orange to pink gradient",
        "lighting": "natural sunlight, soft golden hour glow, minimalist lighting",
        "composition": "center-aligned empty space for text, minimalist, wide shot, --ar 2.35:1",
        "color": "limited color palette: warm orange, soft pink, and white, maximum 3 colors",
        "quality": "4k resolution, high quality, professional photography, no text, no watermark",
        "prompt_template": "{subject}, {env}, {lighting}, {composition}, {color}, {quality}",
    },
    "minimal": {
        "subject": "pure abstract geometry, minimalist lines",
        "env": "pure white background, clean negative space, minimalist graphic elements",
        "lighting": "even bright white light, no shadows",
        "composition": "center-aligned empty space for text, extreme minimalist, --ar 2.35:1",
        "color": "limited color palette: black, white, and one accent color, maximum 2 colors",
        "quality": "4k resolution, vector art style, clean edges, no text, no watermark",
        "prompt_template": "{subject}, {env}, {lighting}, {composition}, {color}, {quality}",
    },
}

def build_cover_prompt(title: str, style: str = "tech") -> str:
    """
    基于“好用”进化规则构建封面 prompt。
    强制背景极简，为标题留出 20% 的视觉空间。
    """
    tpl = COVER_STYLES.get(style, COVER_STYLES["tech"])

    return tpl["prompt_template"].format(
        subject=tpl.get("subject", ""),
        env=tpl.get("env", ""),
        lighting=tpl.get("lighting", ""),
        composition=tpl.get("composition", ""),
        color=tpl.get("color", ""),
        quality=tpl.get("quality", ""),
    )
