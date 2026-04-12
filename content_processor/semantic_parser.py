import re
import logging

logger = logging.getLogger(__name__)

class SemanticParser:
    """
    语义解析器：识别 Markdown 中的结构并自动增强。
    进化点：
      1. 自动识别对话体 (Dialogue) 并套用 :::dialogue
      2. 自动识别多图 (Gallery) 并套用 :::gallery
      3. 自动识别核心观点 (Callout)
    """

    @staticmethod
    def parse(markdown_text: str) -> str:
        text = markdown_text
        
        # 1. 识别对话体
        # 匹配格式如 "张三：内容" 或 "**李四**：内容"
        # 连续 2 条及以上视为对话
        lines = text.splitlines()
        new_lines = []
        in_dialogue = False
        dialogue_buffer = []

        dialogue_pattern = re.compile(r'^(\*\*.*?\*\*|[^:\s]+)[:：]\s*(.*)')

        for line in lines:
            match = dialogue_pattern.match(line.strip())
            if match:
                if not in_dialogue:
                    in_dialogue = True
                dialogue_buffer.append(line)
            else:
                if in_dialogue:
                    if len(dialogue_buffer) >= 2:
                        new_lines.append(":::dialogue")
                        new_lines.extend(dialogue_buffer)
                        new_lines.append(":::")
                    else:
                        new_lines.extend(dialogue_buffer)
                    dialogue_buffer = []
                    in_dialogue = False
                new_lines.append(line)
        
        # 处理结尾遗留的对话
        if in_dialogue:
            if len(dialogue_buffer) >= 2:
                new_lines.append(":::dialogue")
                new_lines.extend(dialogue_buffer)
                new_lines.append(":::")
            else:
                new_lines.extend(dialogue_buffer)

        text = "\n".join(new_lines)

        # 2. 识别连续图片 (Gallery)
        # 3 张以上连续图片（中间只有空行）套用 :::gallery
        img_pattern = re.compile(r'!\[.*?\]\(.*?\)')
        
        def gallery_replacer(match):
            imgs = match.group(0).strip().split('\n')
            imgs = [i.strip() for i in imgs if i.strip()]
            if len(imgs) >= 3:
                return f":::gallery\n" + "\n".join(imgs) + "\n:::"
            return match.group(0)

        # 匹配连续的图片行
        text = re.sub(r'(!\[.*?\]\(.*?\)\s*\n?){3,}', gallery_replacer, text)

        # 3. 识别核心观点 (Callout)
        # 识别 > [!important] 标题 格式并增强
        def callout_replacer(match):
            ctype = match.group(1).lower()
            title = match.group(2)
            content = match.group(3)
            
            icon_map = {
                "important": "💡",
                "tip": "🌟",
                "warning": "⚠️",
                "note": "📝"
            }
            icon = icon_map.get(ctype, "📌")
            
            return (
                f'<section style="margin: 20px 0; padding: 15px; border-left: 5px solid #576b95; background: #f8f9fa; border-radius: 4px;">'
                f'<p style="font-weight: bold; margin-bottom: 5px; color: #576b95;">{icon} {title}</p>'
                f'<p style="margin: 0; color: #333;">{content}</p>'
                f'</section>'
            )

        text = re.sub(r'>\s*\[!(.*?)\]\s*(.*?)\n>\s*(.*)', callout_replacer, text)

        # 4. CJK 排版优化：中英文间自动加空格 (简易版)
        # 匹配 [中文][英文] 或 [英文][中文]
        text = re.sub(r'([\u4e00-\u9fa5])([a-zA-Z0-9])', r'\1 \2', text)
        text = re.sub(r'([a-zA-Z0-9])([\u4e00-\u9fa5])', r'\1 \2', text)

        return text
