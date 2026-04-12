# -*- coding: utf-8 -*-
"""
一键发布文章工具 - 从 Markdown 到微信草稿箱
========================================
1. 语义增强 (Semantic Analysis)
2. 封面生成 (Visual Hook)
3. 自动排版 (WenYan Rendering)
3.5 合规检查
4. 微信推送 (Draft Creation)
5. 记忆引擎记录 (journal.jsonl)
"""
import os
import re
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from content_processor.processor import process_markdown
from img_fallback import generate_cover
from config import BASE_DIR

try:
    from memory_engine import journal
    JOURNAL_AVAILABLE = True
except ImportError:
    JOURNAL_AVAILABLE = False

def _parse_frontmatter(text: str) -> dict:
    """提取 Markdown 文件的 YAML frontmatter。"""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def _count_words(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_command(cmd, cwd=None):
    print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"错误: {result.stderr}")
        return False, result.stderr
    return True, result.stdout

def main():
    parser = argparse.ArgumentParser(description="一键发布 Markdown 到微信公众号")
    parser.add_argument("markdown_file", help="Markdown 文件路径")
    parser.add_argument("--style", default="tech", help="封面风格 (tech/warm/minimal)")
    parser.add_argument("--author", help="作者名")
    
    args = parser.parse_args()
    md_path = Path(args.markdown_file)
    
    if not md_path.exists():
        print(f"错误: 文件不存在 {args.markdown_file}")
        sys.exit(1)
        
    print(f"🚀 开始处理文章: {md_path.name}")
    
    # 1. 语义分析与增强
    print("Step 1: 语义增强 (Dialogue / Gallery / CJK Spacing)...")
    original_text = md_path.read_text(encoding="utf-8")
    enhanced_text = process_markdown(original_text)
    enhanced_path = md_path.parent / f"{md_path.stem}_enhanced.md"
    enhanced_path.write_text(enhanced_text, encoding="utf-8")
    
    # 2. 封面生成
    print("Step 2: 生成封面图 (Visual Hook)...")
    cover_res = generate_cover(md_path.stem, style=args.style)
    if not cover_res["success"]:
        print(f"警告: 封面生成失败，请检查 {cover_res['prompt_file']}")
        thumb_path = None
    else:
        thumb_path = cover_res["path"]
        print(f"✅ 封面已就绪: {thumb_path}")
        
    # 3. 排版渲染 (需要 Node.js 和 wenyan_render.mjs)
    print("Step 3: WenYan 排版渲染...")
    html_path = md_path.parent / f"{md_path.stem}.html"
    success, _ = run_command(["node", "wenyan_render.mjs", str(enhanced_path), str(html_path)])
    if not success:
        print("渲染失败，请确保已安装 Node.js 和 wenyan-cli")
        sys.exit(1)

    # 3.5: 合规检查（BLOCKER 级别问题直接终止）
    print("Step 3.5: 合规检查...")
    check_result = subprocess.run(
        [sys.executable, "compliance_check.py", str(md_path), "--strict"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if check_result.stdout:
        print(check_result.stdout)
    if "BLOCKER" in check_result.stdout or "BLOCKER" in (check_result.stderr or ""):
        print("❌ 存在 BLOCKER 级别合规问题，终止发布。请先修复后再试。")
        sys.exit(1)

    # 4. 发布草稿
    print("Step 4: 推送到微信草稿箱...")
    publish_cmd = [sys.executable, "wechat_api/publisher.py", "--html", str(html_path)]
    if args.author:
        publish_cmd.extend(["--author", args.author])
    if thumb_path:
        publish_cmd.extend(["--thumb-path", thumb_path])
        
    success, output = run_command(publish_cmd)
    if success:
        print("\n" + "="*40)
        print("🎉 发布成功！请前往微信后台预览。")
        print("="*40)
        print(output)

        # 5. 写入记忆引擎
        if JOURNAL_AVAILABLE:
            fm = _parse_frontmatter(original_text)
            slug = md_path.stem
            title = fm.get("title") or md_path.stem
            author = args.author or fm.get("author") or ""
            tags = [t.strip() for t in fm.get("tags", "").split(",") if t.strip()]
            theme_id = fm.get("theme_id") or "pie"
            words = _count_words(enhanced_text)

            # 从 output 中尝试提取 draft_id
            draft_id = None
            mid = re.search(r"media_id[:\s]+(\w+)", output, re.IGNORECASE)
            if mid:
                draft_id = mid.group(1)

            journal.record_article(
                slug=slug,
                title=title,
                source="manual",
                theme_id=theme_id,
                author=author,
                words=words,
                draft_id=draft_id,
                publish_time=_now_iso(),
                tags=tags,
                skill_signals=[
                    {"skill": "semantic_parser", "success": True},
                    {"skill": "img_fallback", "success": cover_res["success"]},
                    {"skill": "wenyan_render", "success": success},
                    {"skill": "publisher", "success": True},
                ],
                phase_trace=[
                    {"phase": "semantic_enhance", "status": "done", "output": str(enhanced_path)},
                    {"phase": "cover_generate", "status": "done" if cover_res["success"] else "failed"},
                    {"phase": "wenyan_render", "status": "done"},
                    {"phase": "compliance_check", "status": "passed"},
                    {"phase": "publish", "status": "done"},
                ],
            )
            print(f"📓 已记录到 journal.jsonl")
    else:
        print("发布失败")
        if JOURNAL_AVAILABLE:
            fm = _parse_frontmatter(original_text)
            journal.record_article(
                slug=md_path.stem,
                title=fm.get("title") or md_path.stem,
                source="manual",
                theme_id=fm.get("theme_id") or "pie",
                author=args.author or fm.get("author") or "",
                words=_count_words(enhanced_text),
                skill_signals=[
                    {"skill": "publisher", "success": False, "error": output[:200]},
                ],
                phase_trace=[
                    {"phase": "publish", "status": "failed", "error": output[:200]},
                ],
                notes="发布失败",
            )

if __name__ == "__main__":
    main()
