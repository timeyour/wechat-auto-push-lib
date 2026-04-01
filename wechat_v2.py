#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pyautogui
import time
import pyperclip

pyautogui.PAUSE = 0.5

# 激活微信
window = pyautogui.getWindowsWithTitle("微信")
if window:
    window[0].activate()
    time.sleep(1)

# 点击搜索框
pyautogui.click(x=250, y=50)
time.sleep(0.5)

# 清空
pyautogui.hotkey("ctrl", "a")
pyautogui.press("backspace")
time.sleep(0.5)

# 用剪贴板粘贴群名
group_name = "一代伟仁"
pyperclip.copy(group_name)
pyautogui.hotkey("ctrl", "v")
time.sleep(1)

# 搜索
pyautogui.press("enter")
time.sleep(1.5)

# 选择第一个结果
pyautogui.press("down")
time.sleep(0.3)
pyautogui.press("enter")
time.sleep(2)

# 用剪贴板粘贴消息
message = "棒"
pyperclip.copy(message)
pyautogui.hotkey("ctrl", "v")
time.sleep(0.5)

# 发送
pyautogui.press("enter")

print("OK!")
