"""公众号文章合规检查工具（v2）

严格按 MEMORY 中「发布前合规检查清单」16项实现：
  红线类 6 项 → 命中任何一条 = 打回不推
  必须类 5 项 → 缺任何一项 = 提醒补上再推
  优化类 5 项 → 不影响发布，建议优化

用法：
  python compliance_check.py article.md
  python compliance_check.py article.md --strict   # 优化类也阻断
"""
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════════════

def _extract_title(text: str) -> str:
    """取第一个 H1 作为标题，否则取 blockquote/正文首行"""
    for line in text.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped.startswith("> "):
            return stripped[2:].strip()
        # 纯 > 开头（无空格）
        if stripped.startswith(">") and len(stripped) > 1:
            return stripped[1:].strip()
        break
    return text.strip().splitlines()[0].strip()[:80]


def _extract_body(text: str) -> str:
    """去掉标题行，返回正文"""
    lines = text.strip().splitlines()
    start = 0
    if lines and lines[0].startswith("# "):
        start = 1
    return "\n".join(lines[start:]).strip()


def _context(text: str, pos: int, before=20, after=20) -> str:
    """取关键词上下文"""
    s = max(0, pos - before)
    e = min(len(text), pos + after)
    return text[s:e].replace("\n", " ")


def _issue(level, rule, word, context, suggestion):
    return {
        "level": level,       # BLOCKER / REQUIRED / SUGGEST
        "rule": rule,
        "word": word,
        "context": context,
        "suggestion": suggestion,
    }


# ═══════════════════════════════════════════════════════════════
#  红线类（BLOCKER）— 命中任何一条 → 打回不推
# ═══════════════════════════════════════════════════════════════

def check_redline_1_ai_auto(text, body):
    """红线1: 非真人自动化创作 — 检查全文是否纯AI生成无人工痕迹"""
    issues = []

    # 指标：文章是否存在个人观点/改编/互动话术/口语化表达
    personal_indicators = [
        r"我觉得", r"我认为", r"个人觉得", r"说实话", r"坦白说",
        r"坦率讲", r"不得不说", r"说实话", r"说实话",
        r"有意思的是", r"最让我.{0,5}(意外|惊讶|吃惊|震惊|好奇)",
        r"你.{0,3}(是不是|有没有|有没有想过|可能)",
        r"问我.{0,5}(怎么|如何|什么)",
        r"我的建议是", r"我的判断是", r"我.{0,3}(用过|试过|踩过|翻过|踩过)",
        r"聊(到|起|聊)", r"说(到|起|说)",
        r"这(就|就)有点", r"说白了", r"简单来说",
    ]
    interaction_indicators = [
        r"你觉得呢", r"你怎么看", r"你怎么选", r"你是哪种",
        r"欢迎在评论区", r"留言区", r"在[看]",
        r"点.{0,3}(赞|在看)",
    ]

    personal_hits = sum(1 for p in personal_indicators if re.search(p, body))
    interaction_hits = sum(1 for p in interaction_indicators if re.search(p, body))

    # AI特征词检测（高密度说明可能是纯AI生成）
    ai_patterns = [
        r"总而言之", r"综上所述", r"值得注意的是", r"不可否认",
        r"毋庸置疑", r"事实上", r"显而易见", r"不言而喻",
        r"在这个.{0,4}(时代|背景下|语境中)", r"随着.{0,10}的发展",
        r"一方面.{0,30}另一方面", r"不仅.{0,15}而且",
        r"在当今", r"当今社会",
    ]
    ai_hits = sum(1 for p in ai_patterns if re.search(p, body))

    # 判定逻辑：有个人痕迹或互动话术 = 有人工介入
    if personal_hits >= 2 or interaction_hits >= 1:
        return issues  # 有人工痕迹，通过

    # AI特征词 >3 且无个人痕迹 → 告警
    if ai_hits >= 4 and personal_hits == 0 and interaction_hits == 0:
        issues.append(_issue(
            "BLOCKER", "非真人创作",
            "AI特征", "检测到大量AI常见表述，缺少个人观点/互动话术",
            "加入个人观点、口语化表达或互动话术，体现人工润色痕迹"
        ))

    return issues


def check_redline_2_political(text, body):
    """红线2: 政治敏感 — 关键词扫描"""
    issues = []
    words = [
        "反党", "反社会", "反国家", "颠覆政权", "分裂国家", "煽动暴乱",
        "恐怖主义", "极端主义", "邪教", "法轮",
        "藏独", "台独", "疆独", "港独",
        "六四", "天安门", "文化大革命",
        "政法委", "中宣部", "网信办",
        "政治体制", "领导人", "国家机密", "意识形态", "阶级斗争",
    ]
    for w in words:
        for m in re.finditer(re.escape(w), text):
            issues.append(_issue(
                "BLOCKER", "政治敏感词",
                w, _context(text, m.start()),
                "立即删除或替换为中性表述"
            ))
    return issues


def check_redline_3_fake_info(body):
    """红线3: 虚假信息 — 伪科学/严重失实关键词"""
    issues = []
    patterns = [
        (r"(包治|根治|药到病除|立竿见影|一针见效)", "医疗虚假承诺"),
        (r"(百分百治愈|永不复发|彻底根治)", "医疗绝对化承诺"),
        (r"(致癌.{0,5}(绝对|一定)|吃.{0,5}致癌)", "食品安全谣言"),
    ]
    for pat, label in patterns:
        for m in re.finditer(pat, body):
            issues.append(_issue(
                "BLOCKER", "虚假信息",
                m.group(), _context(body, m.start()),
                f"删除「{label}」类表述，除非有权威文献支撑"
            ))
    return issues


def check_redline_4_privacy(text):
    """红线4: 个人信息泄露 — 身份证/电话/住址/银行卡"""
    issues = []
    patterns = [
        (r"\b\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b", "疑似身份证号"),
        (r"\b1[3-9]\d{9}\b", "疑似手机号"),
        (r"\b\d{16,19}\b", "疑似银行卡号"),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "疑似邮箱"),
    ]
    for pat, label in patterns:
        for m in re.finditer(pat, text):
            issues.append(_issue(
                "BLOCKER", "个人信息泄露",
                m.group(), _context(text, m.start()),
                f"模糊化处理「{label}」（如 138****5678）"
            ))
    return issues


def check_redline_5_finance(body):
    """红线5: 金融红线 — 荐股/荐基金/证券咨询"""
    issues = []
    patterns = [
        (r"(推荐|建议|强烈建议).{0,10}(买入|持有|加仓|抄底)", "荐股"),
        (r"(涨停|跌停|牛市|熊市).{0,10}(必涨|稳赚|翻倍)", "股市预测"),
        (r"(荐股|内幕|庄家|主力).{0,10}(消息|信号|布局)", "内幕消息"),
        (r"(基金|理财).{0,10}(保本保息|稳赚|零风险|无风险)", "虚假理财承诺"),
        (r"(收益率).{0,5}(100%|200%|翻倍|暴利)", "夸大收益"),
    ]
    for pat, label in patterns:
        for m in re.finditer(pat, body):
            issues.append(_issue(
                "BLOCKER", "金融违规",
                m.group(), _context(body, m.start()),
                f"删除「{label}」类表述，非持牌不得提供证券投资建议"
            ))
    return issues


def check_redline_6_inducement(text, body):
    """红线6: 诱导分享/关注"""
    issues = []
    patterns = [
        r"分享.{0,10}(后|才|就能|即可)(看|领|获取|解锁)",
        r"关注.{0,10}(后|才|即可|回复)(领|看|获取|免费)",
        r"不转.{0,5}(不是|就不是)",
        r"转发.{0,10}(领|抢|免单|白送|红包)",
        r"关注领红包",
    ]
    for pat in patterns:
        for m in re.finditer(pat, body):
            issues.append(_issue(
                "BLOCKER", "诱导分享/关注",
                m.group(), _context(body, m.start()),
                "删除诱导性话术，改为自然引导"
            ))
    return issues


# ═══════════════════════════════════════════════════════════════
#  必须类（REQUIRED）— 缺任何一项 → 提醒补上再推
# ═══════════════════════════════════════════════════════════════

def check_required_7_ai_label(body):
    """必须7: AI内容标注声明"""
    patterns = [
        r"本文.{0,5}(由|部分由).{0,10}AI.{0,10}(辅助|生成|创作|参与)",
        r"AI.{0,5}(辅助|生成|创作|参与).{0,10}(本文|本篇|本文章)",
        r"AI辅助创作",
    ]
    for pat in patterns:
        if re.search(pat, body, re.IGNORECASE):
            return []
    return [_issue(
        "REQUIRED", "AI内容标注",
        "缺失", "",
        "文首或文末添加「本文部分内容由AI辅助创作」（字号≥正文5%）"
    )]


def check_required_8_politics_source(body):
    """必须8: 时政来源标注 — 涉国内时事/政策/社会事件需标来源"""
    # 先判断文章是否涉及时政
    politics_indicators = [
        r"政策", r"法规", r"监管", r"官方(发布|宣布|通报|回应)",
        r"国务院", r"(工信|网信|公安|司法|教育|科技|财政)部",
        r"(人大|政协|两会)",
        r"(新规|新政|条例|规定)发布",
        r"(政府|国家).{0,5}(表态|回应|通报)",
    ]
    has_politics = any(re.search(p, body) for p in politics_indicators)
    if not has_politics:
        return []  # 不涉及时政，无需检查

    # 检查是否有来源标注
    source_patterns = [
        r"来源[：:]", r"据.{0,10}(报道|消息|通报)",
        r"(官方账号|新华社|人民日报|央视).{0,10}(报道|消息)",
    ]
    has_source = any(re.search(p, body) for p in source_patterns)
    if has_source:
        return []

    return [_issue(
        "REQUIRED", "时政来源标注",
        "缺失", "",
        "涉及时政内容，需在正文开头或结尾标注「来源：官方账号全称」"
    )]


def check_required_9_ad_label(body):
    """必须9: 广告标注 — 商业推广内容需标注"""
    # 检测是否包含推广内容
    ad_indicators = [
        r"赞助", r"合作.{0,5}(推广|推广|品牌)", r"广告合作",
        r"(限时|专属).{0,10}(优惠|折扣|促销|立减)",
        r"(购买|下单|抢购|购买链接)",
        r"(优惠券|折扣码|促销码)",
    ]
    has_ad = any(re.search(p, body) for p in ad_indicators)
    if not has_ad:
        return []

    if re.search(r"广告(投放|推广|内容|合作)?[：:]?", body):
        return []  # 已标注

    return [_issue(
        "REQUIRED", "广告标注",
        "缺失", "",
        "包含商业推广内容，需标注「广告」"
    )]


def check_required_10_data_source(body):
    """必须10: 数据来源标注 — 引用数据需注明出处"""
    # 检测是否有数据引用
    data_patterns = [
        r"\d+[\.\d]*\s*[%％]",        # 百分比
        r"\d+[\.\d]*\s*(万|亿|千万|百万|万亿)",  # 大数字
    ]
    has_data = any(re.search(p, body) for p in data_patterns)
    if not has_data:
        return []

    # 检查是否有来源
    source_patterns = [
        r"(根据|据|来自|引用|参考).{0,15}(报告|数据|研究|统计|调查|官方)",
        r"(来源|出处|reference|source)",
        r"(Gartner|IDC|Statista|McKinsey|CB\s?Insights)",
        r"(GitHub|npm|Stack Overflow).{0,10}(数据|统计)",
        r"(GitHub|npm|StackOverflow).{0,3}(显示|统计)",
    ]
    has_source = any(re.search(p, body, re.IGNORECASE) for p in source_patterns)
    if has_source:
        return []

    return [_issue(
        "REQUIRED", "数据来源标注",
        "缺失", "",
        "文章包含数据引用但未标注来源，建议在引用处注明（如「GitHub数据显示」「据XX报告」）"
    )]


def check_required_11_image_source(text):
    """必须11: 图片来源 — 配图需有合法来源说明"""
    # 找所有图片
    images = list(re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', text))
    if not images:
        return []

    # 检查是否有图片来源声明
    source_keywords = [
        r"(图片来源|图片来自|配图.{0,5}(来源|来自)|截图.{0,5}(自|来自))",
        r"(screenshot|captured|generated by)",
    ]
    has_source = any(re.search(p, text, re.IGNORECASE) for p in source_keywords)
    if has_source:
        return []

    # 如果图片数量 <= 3 且都有 alt 描述，降低级别为建议
    all_have_alt = all(m.group(1).strip() for m in images)
    if all_have_alt and len(images) <= 3:
        return [_issue(
            "REQUIRED", "图片来源",
            "缺失", f"共 {len(images)} 张图片",
            "建议在文末或图片旁注明图片来源（如「图片来源：XXX官网截图」「AI生成」）"
        )]

    return [_issue(
        "REQUIRED", "图片来源",
        "缺失", f"共 {len(images)} 张图片",
        "文章含多张配图，需说明图片来源（截图/AI生成/授权图库等）"
    )]


# ═══════════════════════════════════════════════════════════════
#  优化建议类（SUGGEST）— 不影响发布，建议优化
# ═══════════════════════════════════════════════════════════════

# 广告法极限词（上下文白名单用于降低误报）
_AD_LIMIT_WORDS = [
    "最佳", "最优", "最强", "最好", "最大", "最高", "最低",
    "最先进", "最受欢迎", "最安全",
    "唯一", "首个", "首选", "独一无二", "绝无仅有",
    "顶级", "顶尖", "极致", "绝版", "销量冠军", "排名第一",
    "国家级", "世界级", "全网最低", "史上最",
    "王牌", "领袖", "之王", "王者", "统治级",
]

# 单字词 + 白名单上下文（科技文章合理用法）
_SINGLE_CHAR_WHITELIST = {
    "最": [
        r"最值得", r"最重要", r"最核心", r"最关键", r"最为",
        r"最近", r"最初", r"最终", r"最大", r"最小", r"最多", r"最快",
        r"最活跃", r"最流行", r"最常见", r"最基本的", r"最简单的",
        r"最引人注目", r"最热门", r"最好的",
    ],
}

_AD_WHITELIST_CONTEXTS = {
    "第一": [r"第一梯队", r"第一次", r"第一手", r"第一层", r"第一行", r"第一版", r"第一方"],
}


def check_suggest_12_ad_words(body):
    """优化12: 绝对化用语 — 广告法违规"""
    issues = []

    # 多字词检查（含上下文白名单）
    for word in _AD_LIMIT_WORDS:
        ctx_patterns = _AD_WHITELIST_CONTEXTS.get(word, [])
        for m in re.finditer(re.escape(word), body):
            if ctx_patterns:
                local = body[max(0, m.start()-3):min(len(body), m.end()+10)]
                if any(re.search(p, local) for p in ctx_patterns):
                    continue
            issues.append(_issue(
                "SUGGEST", "绝对化用语",
                word, _context(body, m.start()),
                "替换为更客观的表述"
            ))

    return issues


def check_suggest_13_title(title):
    """优化13: 标题合规 — 恐吓/夸大/反常识/假借官方/隐藏关键信息"""
    issues = []

    # 恐吓侮辱
    fear_patterns = [
        r"(不.{0,3}(看|了解|知道)就(死|完了|晚了|惨了))",
        r"(震惊|吓人|恐怖|可怕)",
        r"(赶紧|赶快|立刻|马上).{0,5}(看|转发|收藏)",
    ]
    for pat in fear_patterns:
        if re.search(pat, title):
            issues.append(_issue(
                "SUGGEST", "标题-恐吓/煽动",
                re.search(pat, title).group(), f"标题「{title}」",
                "避免恐吓性标题，改为干货/价值导向"
            ))
            break

    # 无依据夸大
    exaggerate_patterns = [
        r"(揭秘|曝光|黑幕|内幕|真相)(!|！)",
        r"(全网|史上|天下).{0,5}(第一|唯一|最)",
        r"(曝光|揭秘|黑幕).{0,5}真实面目",
    ]
    for pat in exaggerate_patterns:
        if re.search(pat, title):
            issues.append(_issue(
                "SUGGEST", "标题-夸大/无依据",
                re.search(pat, title).group(), f"标题「{title}」",
                "避免无依据夸大，改为具体可验证的信息"
            ))
            break

    # 假借官方
    official_patterns = [
        r"(官方|国务院|央行|工信部?).{0,5}(紧急|突然|刚刚)",
        r"(刚刚|突发|紧急).{0,10}(通知|发布|宣布)",
    ]
    for pat in official_patterns:
        if re.search(pat, title):
            issues.append(_issue(
                "SUGGEST", "标题-假借官方",
                re.search(pat, title).group(), f"标题「{title}」",
                "避免假借官方名义制造紧迫感"
            ))
            break

    return issues


def check_suggest_14_title_length(title):
    """优化14: 标题长度 — 超30字建议断句"""
    if len(title) > 30:
        return [_issue(
            "SUGGEST", "标题过长",
            f"{len(title)}字", f"「{title[:40]}{'...' if len(title)>40 else ''}」",
            f"标题{len(title)}字，建议30字以内；如需保留，用冒号/破折号断句"
        )]
    return []


def check_suggest_15_cta(body):
    """优化15: 文末互动 — 必须有「在看」引导（禁止诱导话术）"""
    # 检查是否有文末互动引导
    cta_patterns = [
        r"在看", r"点赞", r"分享", r"转发",
        r"评论区", r"留言",
        r"觉得.{0,5}(有用|不错|值得)",
        r"(欢迎|欢迎在|欢迎来).{0,5}(留言|评论|讨论)",
    ]
    has_cta = any(re.search(p, body) for p in cta_patterns)

    # 检查是否有诱导话术（如果CTA中包含这些则双重告警）
    bad_cta = re.search(
        r"不(点|转|赞).{0,5}(不是|就不是|后悔)", body
    )

    issues = []
    if not has_cta:
        issues.append(_issue(
            "SUGGEST", "文末互动引导",
            "缺失", "",
            "文末建议添加互动引导（如「觉得有用点个在看」），提升互动率"
        ))
    if bad_cta:
        issues.append(_issue(
            "SUGGEST", "文末-诱导话术",
            bad_cta.group(), _context(body, bad_cta.start()),
            "删除胁迫性互动话术，改为自然引导"
        ))
    return issues


def check_suggest_16_seo(text, body):
    """优化16: 搜索优化 — 关键词堆砌/隐藏文字等SEO作弊"""
    issues = []

    # 关键词堆砌：同一段落中同一关键词出现>3次
    paragraphs = body.split("\n\n")
    for para in paragraphs:
        words_in_para = re.findall(r'[\u4e00-\u9fff]{2,6}', para)
        from collections import Counter
        word_count = Counter(words_in_para)
        for word, count in word_count.items():
            if count > 3 and len(word) >= 2:
                issues.append(_issue(
                    "SUGGEST", "关键词堆砌",
                    f"「{word}」出现{count}次", para[:60] + "...",
                    f"「{word}」在同一短文中出现{count}次，建议精简"
                ))
                break  # 每段只报一次
        if len(issues) >= 3:
            break

    # 隐藏文字：HTML注释、白色文字
    html_patterns = [
        r"<!--.*?-->",  # HTML注释
        r"color\s*:\s*(white|#fff|#ffffff|#FFF|#FFFFFF)",
    ]
    for pat in html_patterns:
        for m in re.finditer(pat, text, re.DOTALL | re.IGNORECASE):
            issues.append(_issue(
                "SUGGEST", "隐藏文字/作弊",
                m.group()[:30], _context(text, m.start()),
                "删除隐藏文字/注释/白色文字等SEO作弊手段"
            ))

    return issues


# ═══════════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════════

def run_check(md_path: str, strict: bool = False) -> bool:
    text = Path(md_path).read_text("utf-8")
    title = _extract_title(text)
    body = _extract_body(text)

    output = []
    def p(msg=""):
        try:
            print(msg)
        except UnicodeEncodeError:
            pass
        output.append(msg)

    p(f"\n{'='*60}")
    p(f"  合规检查报告 v2")
    p(f"  文件: {md_path}")
    p(f"  标题: {title}")
    p(f"  字数: {len(text)} | 行数: {len(text.splitlines())}")
    p(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    p(f"{'='*60}")

    all_issues = []

    # ── 红线类 ──
    p(f"\n  🔴 红线类检查（命中=打回不推）")
    p(f"  {'─'*40}")
    redline_checks = [
        ("1.非真人创作", lambda: check_redline_1_ai_auto(text, body)),
        ("2.政治敏感词", lambda: check_redline_2_political(text, body)),
        ("3.虚假信息",   lambda: check_redline_3_fake_info(body)),
        ("4.个人信息泄露", lambda: check_redline_4_privacy(text)),
        ("5.金融违规",   lambda: check_redline_5_finance(body)),
        ("6.诱导分享/关注", lambda: check_redline_6_inducement(text, body)),
    ]
    for name, fn in redline_checks:
        issues = fn()
        all_issues.extend(issues)
        if not issues:
            p(f"  ✅ {name} — 通过")
        else:
            p(f"  ❌ {name} — {len(issues)}个问题:")
            for iss in issues:
                p(f"      「{iss['word']}」{iss['context']}")
                p(f"      → {iss['suggestion']}")

    # ── 必须类 ──
    p(f"\n  🟡 必须类检查（缺=提醒补上再推）")
    p(f"  {'─'*40}")
    required_checks = [
        ("7.AI内容标注",   lambda: check_required_7_ai_label(body)),
        ("8.时政来源标注", lambda: check_required_8_politics_source(body)),
        ("9.广告标注",     lambda: check_required_9_ad_label(body)),
        ("10.数据来源标注", lambda: check_required_10_data_source(body)),
        ("11.图片来源",    lambda: check_required_11_image_source(text)),
    ]
    for name, fn in required_checks:
        issues = fn()
        all_issues.extend(issues)
        if not issues:
            p(f"  ✅ {name} — 通过")
        else:
            p(f"  ⚠️  {name} — {len(issues)}个问题:")
            for iss in issues:
                p(f"      {iss['context']}")
                p(f"      → {iss['suggestion']}")

    # ── 优化建议类 ──
    p(f"\n  🔵 优化建议类（不影响发布）")
    p(f"  {'─'*40}")
    suggest_checks = [
        ("12.绝对化用语", lambda: check_suggest_12_ad_words(body)),
        ("13.标题合规",   lambda: check_suggest_13_title(title)),
        ("14.标题长度",   lambda: check_suggest_14_title_length(title)),
        ("15.文末互动",   lambda: check_suggest_15_cta(body)),
        ("16.搜索优化",   lambda: check_suggest_16_seo(text, body)),
    ]
    for name, fn in suggest_checks:
        issues = fn()
        all_issues.extend(issues)
        if not issues:
            p(f"  ✅ {name} — 通过")
        else:
            p(f"  💡 {name} — {len(issues)}个建议:")
            for iss in issues:
                p(f"      「{iss['word']}」{iss['context'][:50]}")
                p(f"      → {iss['suggestion']}")

    # ── 汇总 ──
    blockers   = [i for i in all_issues if i["level"] == "BLOCKER"]
    requireds  = [i for i in all_issues if i["level"] == "REQUIRED"]
    suggests   = [i for i in all_issues if i["level"] == "SUGGEST"]

    p(f"\n{'='*60}")
    p(f"  检查结果汇总")
    p(f"{'='*60}")
    p(f"  🔴 红线 (BLOCKER):   {len(blockers)}  {'❌ 打回' if blockers else '✅'}")
    p(f"  🟡 必须 (REQUIRED):  {len(requireds)}  {'⚠️ 需补' if requireds else '✅'}")
    p(f"  🔵 建议 (SUGGEST):   {len(suggests)}  {'💡 优化' if suggests else '✅'}")
    p(f"{'='*60}")

    if blockers:
        p(f"\n  ❌ 存在 {len(blockers)} 个红线问题，必须修复后才能发布")
        passed = False
    elif requireds:
        p(f"\n  ⚠️  有 {len(requireds)} 个必须项缺失，建议补上再推")
        passed = True  # 不阻断，仅提醒
    elif suggests and strict:
        p(f"\n  ⚠️  严格模式下 {len(suggests)} 个建议也视为阻断")
        passed = False
    elif suggests:
        p(f"\n  ✅ 通过（有 {len(suggests)} 个优化建议，建议但不阻断）")
        passed = True
    else:
        p(f"\n  ✅ 全部通过，可以发布")
        passed = True

    # 写报告
    report_path = Path(md_path).with_suffix(".compliance.txt")
    report_path.write_text("\n".join(output), "utf-8")

    return passed


def main():
    parser = argparse.ArgumentParser(description="公众号文章合规检查 v2")
    parser.add_argument("file", help="Markdown 文件路径")
    parser.add_argument("--strict", action="store_true", help="严格模式：建议类也阻断")
    args = parser.parse_args()

    md_path = Path(args.file)
    if not md_path.exists():
        print(f"文件不存在: {md_path}")
        sys.exit(1)

    passed = run_check(str(md_path), args.strict)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
