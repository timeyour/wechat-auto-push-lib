#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地桌面微信辅助发送脚本（可选）

说明：
- 这是一个本地桌面自动化小工具，不属于 RSS -> 草稿箱主流程。
- 需要本机微信窗口可见，并额外安装 pyautogui / pyperclip。
- 所有目标群名、消息内容、点击坐标都通过命令行参数传入，不再写死个人数据。
"""
import argparse
import sys
import time


def parse_args():
    parser = argparse.ArgumentParser(description="本地桌面微信辅助发送脚本")
    parser.add_argument("--group", required=True, help="要搜索并进入的群名或联系人名")
    parser.add_argument("--message", required=True, help="要发送的消息内容")
    parser.add_argument("--search-x", type=int, default=250, help="搜索框 X 坐标")
    parser.add_argument("--search-y", type=int, default=50, help="搜索框 Y 坐标")
    parser.add_argument("--pause", type=float, default=0.5, help="每步操作的默认停顿秒数")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        import pyautogui
        import pyperclip
    except ImportError:
        print("缺少依赖：请先安装 pyautogui 和 pyperclip", file=sys.stderr)
        print("示例：pip install pyautogui pyperclip", file=sys.stderr)
        sys.exit(1)

    pyautogui.PAUSE = args.pause

    window = pyautogui.getWindowsWithTitle("微信")
    if not window:
        print("未找到标题包含“微信”的桌面窗口", file=sys.stderr)
        sys.exit(1)

    window[0].activate()
    time.sleep(1)

    # 点击搜索框并清空现有内容。
    pyautogui.click(x=args.search_x, y=args.search_y)
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("backspace")
    time.sleep(0.5)

    pyperclip.copy(args.group)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1)

    pyautogui.press("enter")
    time.sleep(1.5)
    pyautogui.press("down")
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(2)

    pyperclip.copy(args.message)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)
    pyautogui.press("enter")

    print("OK!")


if __name__ == "__main__":
    main()
