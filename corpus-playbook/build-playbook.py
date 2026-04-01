#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build-playbook.py -- corpus learning: auto-generate writing playbook

Usage:
  python build-playbook.py <topic_id>         generate playbook
  python build-playbook.py <topic_id> --force  force overwrite
  python build-playbook.py list               list existing playbooks
  python build-playbook.py help               show this help

Example:
  python build-playbook.py 1       # Generate playbook for topic #1
  python build-playbook.py list    # Show all existing playbooks
"""

import os
import sys
import json
import time
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
CORPUS_DIR = BASE_DIR / "corpus"
PLAYBOOKS_DIR = BASE_DIR / "playbooks"
LESSONS_DIR = BASE_DIR / "lessons"

TOPICS = {
    1:  {"name": "AI工具实测",     "seo": "2025年最值得用的AI工具",        "format": "横评对比+实操截图+个人评分"},
    2:  {"name": "GitHub热榜解读", "seo": "GitHub热门开源项目推荐",        "format": "项目介绍+实操演示+使用场景"},
    3:  {"name": "效率技巧",       "seo": "程序员效率提升技巧",             "format": "清单式+每条附操作步骤+效果对比"},
    4:  {"name": "Prompt工程",     "seo": "AI Prompt高效写法教程",         "format": "模板展示+原理说明+场景举例"},
    5:  {"name": "开发者工具",     "seo": "程序员必备开发工具",             "format": "工具对比+安装使用+个人推荐理由"},
    6:  {"name": "AI行业观察",     "seo": "AI人工智能行业发展趋势",         "format": "数据支撑+趋势判断+个人观点"},
    7:  {"name": "产品分析",       "seo": "AI产品深度分析",                 "format": "多维度分析+用户场景+优缺点总结"},
    8:  {"name": "技术原理",       "seo": "大语言模型技术原理",             "format": "类比解释+技术要点+实际案例"},
    9:  {"name": "创业思考",       "seo": "AI时代创业机会分析",             "format": "个人经历+具体数据+可复制方法"},
    10: {"name": "AI替代观察",    "seo": "哪些职业最容易被AI替代",         "format": "岗位对比+数据支撑+应对建议"},
    11: {"name": "新手入门",      "seo": "AI使用入门教程",                 "format": "步骤引导+截图说明+常见问题"},
    12: {"name": "工具对比",      "seo": "AI工具对比评测推荐",             "format": "维度打分+场景推荐+结论表格"},
    13: {"name": "自动化流程",    "seo": "AI自动化工作流搭建教程",         "format": "流程图+每步工具+代码配置示例"},
    14: {"name": "本地部署",      "seo": "AI模型本地部署教程",             "format": "环境准备+步骤命令+效果展示"},
    15: {"name": "API接入",       "seo": "AI API接口接入教程",             "format": "代码示例+成本计算+踩坑记录"},
    16: {"name": "技术解读",      "seo": "AI技术深度解读",                 "format": "核心概念+技术细节+应用场景"},
    17: {"name": "观点输出",      "seo": "AI行业观点与思考",               "format": "观点鲜明+逻辑支撑+反例讨论"},
    18: {"name": "避坑指南",      "seo": "AI使用常见误区",                 "format": "问题列举+原因分析+正确做法"},
    19: {"name": "行业预测",      "seo": "2025年AI发展预测",               "format": "趋势列表+数据预测+时间节点"},
    20: {"name": "冷知识",        "seo": "AI有趣冷知识盘点",               "format": "趣味清单+轻松叙述+配图增强"},
    21: {"name": "个人故事",      "seo": "程序员成长故事分享",             "format": "时间线叙事+具体数字+经验总结"},
    22: {"name": "案例拆解",      "seo": "AI实战案例详细拆解",             "format": "背景介绍+具体做法+效果数据"},
    23: {"name": "幕后花絮",      "seo": "内容创作幕后故事",               "format": "过程还原+数据展示+反思总结"},
    24: {"name": "失败复盘",      "seo": "AI项目失败案例复盘",             "format": "项目背景+失败原因+可复用教训"},
    25: {"name": "资源合集",      "seo": "AI工具资源大全",                 "format": "分类列表+链接+简要说明"},
    26: {"name": "Prompt合集",    "seo": "AI提示词模板大全",               "format": "分类Prompt+使用场景+效果说明"},
    27: {"name": "书单推荐",      "seo": "AI与编程必读书单",               "format": "书籍列表+每本一句话推荐+阅读顺序"},
    28: {"name": "工具清单",      "seo": "程序员必备工具清单",             "format": "分类工具+用途说明+获取方式"},
    29: {"name": "热点追踪",      "seo": "AI热点事件深度解读",             "format": "事件回顾+多方观点+我的判断"},
    30: {"name": "选题参考",      "seo": "公众号选题灵感库",               "format": "选题列表+切入角度+SEO关键词"},
}


def ensure_dirs():
    for d in [CORPUS_DIR, PLAYBOOKS_DIR, LESSONS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def list_corpus_files():
    if not CORPUS_DIR.exists():
        return []
    return [f for f in CORPUS_DIR.iterdir() if f.suffix in {'.md', '.txt'}]


def read_corpus():
    files = list_corpus_files()
    if not files:
        return "", 0
    contents = []
    for f in sorted(files):
        try:
            text = f.read_text(encoding='utf-8')
            contents.append("# " + f.stem + "\n\n" + text + "\n")
        except Exception as e:
            print("WARNING: failed to read " + f.name + ": " + str(e), file=sys.stderr)
    return "\n\n---\n\n".join(contents), len(files)


def read_lessons():
    if not LESSONS_DIR.exists():
        return ""
    lessons = []
    for f in sorted(LESSONS_DIR.glob("*.json"))[:10]:
        try:
            lessons.append(json.loads(f.read_text(encoding='utf-8')))
        except Exception:
            pass
    return json.dumps(lessons, ensure_ascii=False, indent=2)


def detect_style(text):
    if not text:
        return {"avg_paragraph_len": 0, "uses_numbers": False,
                "has_steps": False, "has_questions": False, "conclusion_style": "none",
                "file_count": 0}
    paras = [p.strip() for p in text.split('\n\n') if p.strip()]
    avg_len = sum(len(p) for p in paras) / max(len(paras), 1)
    uses_numbers = bool(re.search(r'[一二三四五六七八九十百千万\d]', text[:2000]))
    has_steps = bool(re.search(r'(第[一二三四五六七八九十\d]+步|步骤|Step \d)', text))
    has_questions = text.count('\uff1f') + text.count('?') > 0
    conclusion = "concise"
    if '\u603b\u7ed3' in text[:500]:
        conclusion = "summary"
    elif '\u603b\u4e4b' in text[:500]:
        conclusion = "takeaway"
    elif '\u4f60\u600e\u4e48\u770b' in text[:500]:
        conclusion = "interactive"
    return {
        "avg_paragraph_len": round(avg_len, 1),
        "uses_numbers": uses_numbers,
        "has_steps": has_steps,
        "has_questions": has_questions,
        "conclusion_style": conclusion,
        "file_count": len(list_corpus_files()),
    }


STRUCT_MAP = {
    "横评": [
        "** Module A: Horizontal Comparison",
        "- Each tool/project gets its own section: name + one-line positioning + core data",
        "- Comparison dimensions: ease of use / effect / cost-performance",
        "- Conclusion: recommendations by scenario",
        "",
        "** Module B: Hands-on Demo",
        "- 1 key screenshot per tool",
        "- Numbered steps: 1. -> 2. -> 3.",
        "- Wrap key parameters in code blocks",
        "",
        "** Module C: Personal Rating",
        "- 10-point scale with reasoning",
        "- Suitable audience tags",
    ],
    "教程": [
        "** Module A: Background and Prerequisites",
        "- What problem does this solve? What basics are needed?",
        "- Environment requirements list (tool versions, OS, etc.)",
        "",
        "** Module B: Step-by-step Operation",
        "- Each step with 'Step X:' heading",
        "- Wrap commands in code blocks",
        "- Include common errors and solutions",
        "",
        "** Module C: Result Verification",
        "- How to confirm success? (screenshot/command output)",
        "",
        "** Module D: Further Reading",
        "- Related topics (link to existing articles)",
    ],
    "观点": [
        "** Module A: Core Viewpoint (Front-loaded)",
        "- State the viewpoint in one sentence (bold)",
        "- Complete in 300 chars, no more than 20% of article",
        "",
        "** Module B: Evidence Support",
        "- At least 2-3 specific cases or data points",
        "- Source notes after each evidence",
        "",
        "** Module C: Counter-argument Discussion",
        "- Acknowledge opposing views (1 paragraph)",
        "- Explain why your core viewpoint still holds",
        "",
        "** Module D: Reader Engagement",
        "- Closing question: 'Do you agree?'",
    ],
    "洞察": [
        "** Module A: Industry/Product Background",
        "- Introduce with specific numbers or events (with source)",
        "- Let readers understand context in 30 seconds",
        "",
        "** Module B: Multi-dimension Breakdown",
        "- Follow 'what -> why -> how' structure",
        "- Each dimension 300-500 chars",
        "- Use numbered sub-headings",
        "",
        "** Module C: Personal Judgment",
        "- Clear position (not neutral)",
        "- Attach decision rationale",
        "",
        "** Module D: Actionable Recommendations",
        "- What does this mean for the reader?",
        "- What can they do next?",
    ],
    "合集": [
        "** Module A: Introduction",
        "- Tell readers what scenarios this collection covers",
        "- Explain filtering criteria",
        "",
        "** Module B: Item-by-item Introduction",
        "- Each item: name + one-sentence description + how to get it",
        "- Organized by category (Must-read / Advanced / Tools)",
        "",
        "** Module C: Usage Tips",
        "- Priority/scenario-based recommendations",
        "- Personal usage tips",
        "",
        "** Module D: Ongoing Updates",
        "- How to get the latest version",
    ],
    "故事": [
        "** Module A: Background Setup",
        "- Start with timeline (year/month numbers)",
        "- Let readers get into your narrative rhythm",
        "",
        "** Module B: Core Experience",
        "- Tell story chronologically, highlight key moments",
        "- For failures: write details, not just 'I failed'",
        "",
        "** Module C: Reflection",
        "- What did you learn?",
        "- What value can readers extract?",
        "",
        "** Module D: Data Evidence",
        "- Specific numbers are most persuasive",
        "- Before/after comparison if available",
    ],
    "通用": [
        "** Module A: Problem/Phenomenon Introduction",
        "- Specific scenario + data support",
        "",
        "** Module B: Analysis",
        "- 300-500 chars per module, total 2-4 modules",
        "- Sub-headings in 'number + core point' format",
        "",
        "** Module C: Summary and CTA",
        "- 3-sentence summary",
        "- Interactive question + 'like' prompt",
    ],
}


def get_structure_key(topic_id):
    if topic_id in [1, 2, 12]:
        return "横评"
    elif topic_id in [11, 13, 14, 15, 16]:
        return "教程"
    elif topic_id in [17, 18, 19, 20]:
        return "观点"
    elif topic_id in [6, 7, 8, 9]:
        return "洞察"
    elif topic_id in [25, 26, 27, 28]:
        return "合集"
    elif topic_id in [21, 22, 23, 24]:
        return "故事"
    return "通用"




def load_hot_data():
    """Load today's hot data from GitHub + Twitter JSON files."""
    hot = {"github": [], "twitter": [], "has_data": False}
    data_dir = BASE_DIR / "data"

    gh_file = data_dir / "github_trending.json"
    if gh_file.exists():
        try:
            data = json.loads(gh_file.read_text(encoding="utf-8"))
            repos = data.get("ai_repos", []) or data.get("repos", [])
            for r in repos[:5]:
                hot["github"].append({
                    "name": r.get("name", ""),
                    "desc": r.get("description", "")[:80],
                    "stars": r.get("stars", 0),
                    "lang": r.get("language", ""),
                    "url": r.get("url", ""),
                })
            hot["has_data"] = True
        except Exception:
            pass

    tw_file = data_dir / "twitter_trending.json"
    if tw_file.exists():
        try:
            data = json.loads(tw_file.read_text(encoding="utf-8"))
            for item in data.get("items", [])[:5]:
                hot["twitter"].append({
                    "title": (item.get("title") or item.get("user") or "")[:80],
                    "user": item.get("user", ""),
                    "prob": item.get("probability", 0),
                    "age": item.get("fresh_label", ""),
                    "url": item.get("link", ""),
                })
            hot["has_data"] = True
        except Exception:
            pass

    return hot


def generate_playbook(topic_id, corpus_text, style, lessons_json):
    topic = TOPICS.get(topic_id, {})
    topic_name = topic.get("name", "Topic #" + str(topic_id))
    seo = topic.get("seo", "")
    fmt = topic.get("format", "")

    hot = load_hot_data()

    style_notes = []
    if style["uses_numbers"]:
        style_notes.append("- Good at using numbers and sequence to organize content")
    if style["has_steps"]:
        style_notes.append("- Uses step-by-step structure")
    if style["avg_paragraph_len"] > 150:
        style_notes.append("- Long paragraphs (avg %.0f chars), suitable for deep content" % style["avg_paragraph_len"])
    else:
        style_notes.append("- Short paragraphs (avg %.0f chars), snappy rhythm" % style["avg_paragraph_len"])
    if style["has_questions"]:
        style_notes.append("- Good at using questions to engage readers")
    style_str = "\n".join(style_notes) if style_notes else "- No clear style pattern yet"

    lessons_note = ""
    try:
        lessons_data = json.loads(lessons_json) if lessons_json else []
        if lessons_data:
            lines = ["## Common Revision Points"]
            for l in lessons_data:
                if l.get("error_type"):
                    lines.append("  - [" + l.get("error_type", "") + "] " + l.get("description", ""))
            if len(lines) > 1:
                lessons_note = "\n".join(lines[:6])
    except Exception:
        pass

    struct_key = get_structure_key(topic_id)
    struct_lines = STRUCT_MAP.get(struct_key, STRUCT_MAP["通用"])

    playbook = (
        "# Writing Playbook -- " + topic_name + "\n\n"
        + "> Generated: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n"
        + "> Topic ID: " + str(topic_id) + "\n"
        + "> Corpus: " + str(style.get("file_count", 0)) + " historical articles\n"
        + "> To update: run 'python build-playbook.py " + str(topic_id) + "'\n\n"
        + "---\n\n"
        + "## Topic Metadata\n\n"
        + "| Field | Content |\n"
        + "|-------|---------|\n"
        + "| Topic Name | " + topic_name + " |\n"
        + "| SEO Keywords | " + seo + " |\n"
        + "| Recommended Format | " + fmt + " |\n\n"
    )

    # Add hot data section if available
    if hot["has_data"]:
        hot_sections = []
        if hot["github"]:
            gh_lines = ["## Today's Hot GitHub Repos\n"]
            for i, r in enumerate(hot["github"], 1):
                gh_lines.append(
                    "%d. **%s** (%s) %s stars\n"
                    "   %s\n"
                    "   Link: %s\n" % (
                        i, r["name"], r.get("lang", "?"),
                        r["stars"], r["desc"], r["url"]
                    )
                )
            hot_sections.append("\n".join(gh_lines))
        if hot["twitter"]:
            tw_lines = ["## Today's Hot Twitter Posts\n"]
            for i, t in enumerate(hot["twitter"], 1):
                tw_lines.append(
                    "%d. **[%s%%]** %s | %s\n"
                    "   %s\n" % (
                        i, t["prob"], t.get("user", ""),
                        t.get("age", ""), t["title"]
                    )
                )
            hot_sections.append("\n".join(tw_lines))
        playbook += "---\n\n" + "\n\n---\n\n".join(hot_sections) + "\n\n---\n\n"

    playbook += "## Content Structure Template\n\n"
    playbook += "Recommended format: **" + fmt + "**\n\n"
    playbook += "### Standard Opening (first 300 chars)\n\n"
    playbook += "1. **Pain Point Resonance** (50-80 chars)\n"
    playbook += "   - Open with a specific scenario or data to resonate\n"
    playbook += "   - Avoid vague openings like 'with the development of AI...'\n\n"
    playbook += "2. **Content Preview** (1-2 sentences)\n"
    playbook += "   - Clearly tell readers what this article solves\n"
    playbook += "   - End with 'This article will...' pattern\n\n"
    playbook += "### Main Modules\n\n"
    playbook += "\n".join(struct_lines)
    playbook += "\n\n"
    playbook += "---\n\n"
    playbook += "## Style Guidelines\n\n"
    playbook += "From analysis of " + str(style.get("file_count", 0)) + " historical articles:\n\n"
    playbook += style_str + "\n\n"
    playbook += "### Title Rules\n"
    playbook += "- Length: 15-25 chars (optimal for WeChat search)\n"
    playbook += '- Structure: core info + hook/numbers (e.g. "Tested 14 tools, this 1 is most worth it")\n'
    playbook += "- SEO front-loaded: core search term in first half of title\n"
    playbook += "- Avoid clickbait (algorithm penalty)\n\n"
    playbook += "### Body Rules\n"
    playbook += "- Paragraph <= 5 lines, bold key points\n"
    playbook += "- Max 3 colors (black, dark gray, accent)\n"
    playbook += "- Use <p> not <ul><li> for lists (WeChat HTML compatibility)\n"
    playbook += '- Images must have style="width:100%"\n\n'
    playbook += "### Closing Rules\n"
    playbook += "- 3-sentence summary\n"
    playbook += '- Interactive question ("What do you think...?")\n'
    playbook += '- "Like" prompt ("If this helped, tap the like button")\n\n'

    if lessons_note:
        playbook += "---\n\n" + lessons_note + "\n\n"

    playbook += (
        "---\n\n"
        + "## Compliance Checklist\n\n"
        + "- [x] AI content label: 'This article was partially assisted by AI'\n"
        + "- [x] Data source citation\n"
        + "- [x] Image source note\n"
        + "- [x] Title <= 30 chars\n"
        + "- [ ] No exaggerated claims\n"
        + "- [ ] No competitor disparagement\n\n"
        + "---\n\n"
        + "## GEO Optimization (AI Engine Citation)\n\n"
        + "For topic: **" + topic_name + "**\n\n"
        + "1. **Modular structure**: summary->detail->summary, easiest for AI to cite\n"
        + '2. **Q&A format**: End each module with "Q: XX? A: XX."\n'
        + '3. **Specific numbers**: "improved from 500 to 5000" beats "significantly improved"\n'
        + "4. **Precise terminology**: Define terms when first used\n"
        + "5. **Conclusion first**: Lead with conclusion sentence in each section\n\n"
        + "---\n\n"
        + "*Auto-generated by build-playbook.py*\n"
        + "Run to update: `python build-playbook.py " + str(topic_id) + "`\n"
    )

    return playbook


def get_playbook_path(topic_id):
    topic = TOPICS.get(topic_id, {})
    name = topic.get("name", "topic" + str(topic_id))
    safe_name = "".join(c if c.isalnum() else "_" for c in name)
    return PLAYBOOKS_DIR / (str(topic_id).zfill(2) + "_" + safe_name + ".md")


def build_playbook(topic_id, force=False):
    ensure_dirs()
    if topic_id not in TOPICS:
        print("ERROR: Unknown topic ID: " + str(topic_id))
        print("   Available IDs: 1-" + str(max(TOPICS.keys())))
        sys.exit(1)

    topic = TOPICS[topic_id]
    out_path = get_playbook_path(topic_id)

    print("Reading corpus from: " + str(CORPUS_DIR))
    corpus_text, n_files = read_corpus()
    print("  Found " + str(n_files) + " historical articles")

    print("Analyzing writing style...")
    style = detect_style(corpus_text)
    print("  Avg paragraph length: " + str(style["avg_paragraph_len"]) + " chars")
    print("  Uses numbers: " + ("yes" if style["uses_numbers"] else "no"))
    print("  Step-by-step structure: " + ("yes" if style["has_steps"] else "no"))
    print("  Opening style: " + style["conclusion_style"])

    print("Reading revision feedback...")
    lessons = read_lessons()
    lessons_count = 0
    try:
        lessons_count = len(json.loads(lessons)) if lessons else 0
    except Exception:
        pass
    print("  Found " + str(lessons_count) + " revision records")

    print("Generating playbook...")
    content = generate_playbook(topic_id, corpus_text, style, lessons)
    out_path.write_text(content, encoding='utf-8')

    size = out_path.stat().st_size
    topic_name_out = topic.get("name", "Topic #" + str(topic_id))
    fmt_out = topic.get("format", "")
    print("\nDONE: " + out_path.name + " (" + str(size // 1024) + "KB)")
    print("  Topic: " + topic_name_out + " | Format: " + fmt_out)
    return out_path


def list_playbooks():
    ensure_dirs()
    files = sorted(PLAYBOOKS_DIR.glob("*.md"))
    if not files:
        print("No playbooks yet. Run: python build-playbook.py <topic_id>")
        return
    print("Existing playbooks:\n")
    for f in files:
        stat = f.stat()
        mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
        size_kb = stat.st_size // 1024
        print("  [" + f.stem[:2] + "] " + f.stem + " | " + mtime + " | " + str(size_kb) + "KB")
    print()
    print("Corpus: " + str(len(list_corpus_files())) + " articles")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    if args[0] == "list":
        list_playbooks()
        return

    try:
        topic_id = int(args[0])
    except ValueError:
        print("ERROR: Invalid topic ID: " + args[0])
        print("  Usage: python build-playbook.py <topic_id>")
        sys.exit(1)

    force = "--force" in args or "-f" in args
    ensure_dirs()

    out_path = get_playbook_path(topic_id)
    if out_path.exists() and not force:
        print("WARNING: Already exists: " + out_path.name)
        print("  Force: python build-playbook.py " + str(topic_id) + " --force")
        resp = input("Overwrite? [y/N] ").strip().lower()
        if resp != "y":
            print("Cancelled.")
            return

    build_playbook(topic_id, force=force)


if __name__ == "__main__":
    main()
