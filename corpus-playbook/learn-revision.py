#!/usr/bin/env python3
"""
learn-revision.py — 改稿反馈学习

用法:
  python learn-revision.py add <ai_draft.md> <human_revision.md>
      → 对比两份文档，存入 lessons/，供 playbook 更新参考

  python learn-revision.py list
      → 查看已有改稿记录

  python learn-revision.py stats
      → 显示改稿统计（自动反馈给 playbook）

  python learn-revision.py clear
      → 清空所有改稿记录

原理: 每积累5条改稿 → 运行 build-playbook.py 更新写作手册
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
LESSONS_DIR = BASE_DIR / "lessons"
LESSONS_DIR.mkdir(exist_ok=True)

AUTO_UPDATE_THRESHOLD = 5  # 积累N条改稿后自动更新 playbook


def extract_diff_lines(ai_text: str, human_text: str) -> list:
    """基于规则的差异提取（无需AI，纯文本比较）"""
    diffs = []

    # 1. 段落长度对比
    ai_paras = [p.strip() for p in ai_text.split('\n\n') if p.strip()]
    hu_paras = [p.strip() for p in human_text.split('\n\n') if p.strip()]

    if ai_paras and hu_paras:
        avg_ai = sum(len(p) for p in ai_paras) / len(ai_paras)
        avg_hu = sum(len(p) for p in hu_paras) / len(hu_paras)
        if abs(avg_ai - avg_hu) > 50:
            if avg_hu < avg_ai:
                diffs.append({
                    "type": "段落压缩",
                    "ai": f"平均段落 {avg_ai:.0f} 字",
                    "human": f"压缩至 {avg_hu:.0f} 字",
                    "advice": "段落应更简短，每段聚焦一个信息点",
                })
            else:
                diffs.append({
                    "type": "段落展开",
                    "ai": f"平均段落 {avg_ai:.0f} 字",
                    "human": f"扩展至 {avg_hu:.0f} 字",
                    "advice": "适当展开论述，增加信息密度",
                })

    # 2. 数字使用对比
    ai_nums = len(re.findall(r'\d+', ai_text))
    hu_nums = len(re.findall(r'\d+', human_text))
    if ai_nums < hu_nums * 0.8:
        diffs.append({
            "type": "数据不足",
            "ai": f"含 {ai_nums} 个数字",
            "human": f"含 {hu_nums} 个数字",
            "advice": "增加具体数字、统计数据，提升可信度",
        })

    # 3. 人称对比（"我"/"你"使用）
    ai_first = len(re.findall(r'[你我他]', ai_text[:1000]))
    hu_first = len(re.findall(r'[你我他]', human_text[:1000]))
    if ai_first < hu_first * 0.7:
        diffs.append({
            "type": "人称缺失",
            "ai": f"前1000字含 {ai_first} 句人称",
            "human": f"含 {hu_first} 句人称",
            "advice": "增加第一人称叙述，增强代入感",
        })

    # 4. 问句对比
    ai_q = ai_text.count('？') + ai_text.count('?')
    hu_q = human_text.count('？') + human_text.count('?')
    if ai_q < hu_q:
        diffs.append({
            "type": "互动不足",
            "ai": f"含 {ai_q} 个问句",
            "human": f"含 {hu_q} 个问句",
            "advice": "增加问句引导读者思考，提升互动",
        })

    # 5. 感叹句对比
    ai_excl = ai_text.count('！')
    hu_excl = human_text.count('！')
    if ai_excl < hu_excl * 0.6:
        diffs.append({
            "type": "语气平淡",
            "ai": f"含 {ai_excl} 个感叹句",
            "human": f"含 {hu_excl} 个感叹句",
            "advice": "适当增加感叹句，提升感染力",
        })

    # 6. 标题对比
    ai_h1 = re.findall(r'^#+\s*(.+?)\s*$', ai_text, re.MULTILINE)
    hu_h1 = re.findall(r'^#+\s*(.+?)\s*$', human_text, re.MULTILINE)
    if len(hu_h1) > len(ai_h1) * 1.2:
        diffs.append({
            "type": "结构不足",
            "ai": f"含 {len(ai_h1)} 个小标题",
            "human": f"含 {len(hu_h1)} 个小标题",
            "advice": "增加小标题（数字+核心点格式），便于AI拆解引用",
        })

    return diffs


def read_file(path: str) -> str:
    """读取文件，优先 UTF-8"""
    p = Path(path)
    if not p.exists():
        print(f"❌ 文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        return p.read_text(encoding='utf-8')
    except Exception:
        return p.read_text(encoding='gbk', errors='replace')


def add_revision(ai_path: str, human_path: str) -> dict:
    """添加一条改稿记录"""
    ai_text = read_file(ai_path)
    human_text = read_file(human_path)

    diffs = extract_diff_lines(ai_text, human_text)

    # 生成记录
    record = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "ai_source": Path(ai_path).name,
        "human_source": Path(human_path).name,
        "timestamp": datetime.now().isoformat(),
        "diffs": diffs,
        "auto_summary": f"发现 {len(diffs)} 处可改进点",
    }

    # 保存
    out_file = LESSONS_DIR / f"{record['id']}.json"
    out_file.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"\n📝 改稿记录已保存: {out_file.name}")
    print(f"   AI稿 vs 人工稿 → {len(diffs)} 处改进点\n")

    if diffs:
        print("🔍 改进分析：")
        for i, d in enumerate(diffs, 1):
            print(f"  {i}. [{d['type']}]")
            print(f"     AI:  {d['ai']}")
            print(f"     人工: {d['human']}")
            print(f"     → {d['advice']}\n")

    # 检查是否达到自动更新阈值
    existing = sorted(LESSONS_DIR.glob("*.json"))
    count = len(existing)
    print(f"📊 当前改稿记录: {count} 条")
    if count >= AUTO_UPDATE_THRESHOLD:
        print(f"\n🎉 已积累 {AUTO_UPDATE_THRESHOLD} 条改稿！")
        print("   运行以下命令更新所有写作手册：")
        print("   python build-playbook.py <话题ID> --force")
        print("   （建议对涉及的话题分别运行）")

    return record


def list_lessons():
    """列出所有改稿记录"""
    files = sorted(LESSONS_DIR.glob("*.json"), reverse=True)
    if not files:
        print("[empty] 暂无改稿记录")
        print("   用法: python learn-revision.py add <ai_draft.md> <human_revision.md>")
        return

    print(f"📚 改稿记录 ({len(files)} 条)：\n")
    for f in files:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            ts = data['timestamp'][:16].replace('T', ' ')
            n = len(data.get('diffs', []))
            print(f"  [{ts}] {data['ai_source']} → {data['human_source']}")
            print(f"       {data['auto_summary']}")
            print()
        except Exception as e:
            print(f"  ⚠️  读取失败: {f.name} ({e})")


def show_stats():
    """显示改稿统计"""
    files = sorted(LESSONS_DIR.glob("*.json"))
    if not files:
        print("[empty] 暂无改稿记录")
        return

    all_types = {}
    for f in files:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            for d in data.get('diffs', []):
                t = d['type']
                all_types[t] = all_types.get(t, 0) + 1
        except Exception:
            pass

    print(f"📊 改稿统计（共 {len(files)} 条记录）\n")
    sorted_types = sorted(all_types.items(), key=lambda x: -x[1])
    for t, n in sorted_types:
        bar = "█" * n + "░" * (10 - n)
        print(f"  {t:<12} {bar} ×{n}")
    print(f"\n🎯 最高频改进点: {sorted_types[0][0] if sorted_types else '暂无'}")
    print("\n💡 将这些改进点内化到 prompt 中，AI写作将越来越精准")


def clear_lessons():
    """清空所有改稿记录"""
    files = list(LESSONS_DIR.glob("*.json"))
    if not files:
        print("[empty] 暂无改稿记录")
        return
    print(f"⚠️  确定要删除 {len(files)} 条改稿记录？")
    resp = input("输入 'yes' 确认: ").strip()
    if resp.lower() == 'yes':
        for f in files:
            f.unlink()
        print("✅ 已清空")
    else:
        print("取消。")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        return

    cmd = args[0]

    if cmd == 'add':
        if len(args) < 3:
            print(__doc__)
            print("❌ 用法: python learn-revision.py add <ai_draft.md> <human_revision.md>")
            sys.exit(1)
        add_revision(args[1], args[2])

    elif cmd == 'list':
        list_lessons()

    elif cmd == 'stats':
        show_stats()

    elif cmd == 'clear':
        clear_lessons()

    else:
        print(f"❌ 未知命令: {cmd}")
        print("   可用命令: add / list / stats / clear")


if __name__ == '__main__':
    main()
