#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import edge_tts
import sys

async def main():
    text = "一闪一闪亮晶晶"
    output_file = r"c:\Users\lixin\WorkBuddy\Claw\star.mp3"
    
    # 使用微软晓晓的声音（中文女声）
    communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
    await communicate.save(output_file)
    print("OK: " + output_file)

if __name__ == "__main__":
    asyncio.run(main())
