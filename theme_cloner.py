# -*- coding: utf-8 -*-
"""
主题克隆助手 (Theme Cloner)
==========================
1. 抓取 URL
2. 提取核心样式组件 (Collector)
3. 调用 AI 分析设计规范 (AI Stylist)
4. 生成 WenYan 主题配置 (Generator)
"""

import requests
import json
import argparse
from bs4 import BeautifulSoup
from pathlib import Path

def fetch_wechat_styles(url_or_path):
    """抓取并提取微信文章中的核心样式块（支持 URL 或 本地路径）"""
    print(f"正在分析: {url_or_path}")
    
    html_content = ""
    if url_or_path.startswith("http"):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        try:
            resp = requests.get(url_or_path, headers=headers, timeout=15)
            resp.raise_for_status()
            html_content = resp.text
        except Exception as e:
            print(f"抓取失败: {e}")
            return None
    else:
        path = Path(url_or_path)
        if path.exists():
            html_content = path.read_text(encoding="utf-8")
        else:
            print(f"文件不存在: {url_or_path}")
            return None

    soup = BeautifulSoup(html_content, 'lxml')
    
    # 提取核心样式元素
    style_blocks = []
    
    # 1. 查找所有带 style 的 section/div (微信排版的核心容器)
    for tag in ['section', 'div', 'blockquote']:
        for s in soup.find_all(tag, style=True):
            style_blocks.append({
                "tag": tag,
                "style": s['style'],
                "text_preview": s.get_text(strip=True)[:30]
            })
            if len(style_blocks) >= 20: break
            
    # 2. 查找标题
    for h_tag in ['h1', 'h2', 'h3']:
        for h in soup.find_all(h_tag, style=True):
            style_blocks.append({
                "tag": h_tag,
                "style": h['style'],
                "text_preview": h.get_text(strip=True)
            })
                
    return style_blocks

def analyze_with_ai(style_blocks):
    """
    [占位] 这里将来可以调用 DashScope/Gemini API
    目前先输出分析请求描述，让用户在对话框中让 AI 处理。
    """
    prompt = """
请分析以下微信文章的 CSS 样式片段，并提取设计规范：
1. 主色调 (Primary Color)
2. 标题样式 (H2/H3 的边框、背景、颜色)
3. 正文字体大小与行间距
4. 引用块 (Blockquote) 的风格

样式数据：
"""
    for i, block in enumerate(style_blocks):
        prompt += f"\n[{i+1}] Tag: {block['tag']}\nStyle: {block['style']}\n"
        
    return prompt

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="公众号主题克隆助手")
    parser.add_argument("url", help="微信公众号文章链接")
    parser.add_argument("--output", "-o", help="保存提取结果的文件路径")
    
    args = parser.parse_args()
    
    blocks = fetch_wechat_styles(args.url)
    if blocks:
        ai_prompt = analyze_with_ai(blocks)
        
        if args.output:
            Path(args.output).write_text(ai_prompt, encoding="utf-8")
            print(f"分析请求已保存至: {args.output}")
        else:
            print("\n" + "="*20 + " AI 分析请求 " + "="*20)
            print(ai_prompt)
            print("="*53)
            print("\n💡 提示：你可以将以上内容复制给 AI，让它帮你生成 WenYan 主题配置。")
