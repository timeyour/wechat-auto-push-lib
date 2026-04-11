# wechat-auto-push-lib

> 公众号内容工厂的执行层：RSS 抓取 → 内容清洗 → wenyan 排版 → 草稿箱创建。

> 方法层 SOP 见 [wechat-ops-sop](https://github.com/timeyour/wechat-ops-sop)

> 这不是完整 CMS，而是一个偏个人/小团队的自动化流水线：帮你把外部内容整理成公众号草稿，最终群发仍建议人工确认。

---

## 3 分钟开始

```bash
git clone https://github.com/timeyour/wechat-auto-push-lib.git && cd wechat-auto-push-lib && cp .env.example .env && pip install -r requirements.txt && python main.py --dry
```

---

[![Stars](https://img.shields.io/github/stars/timeyour/wechat-auto-push-lib?style=social)](https://github.com/timeyour/wechat-auto-push-lib/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![WeChat](https://img.shields.io/badge/WeChat-Official%20Account-blue.svg)](https://mp.weixin.qq.com)

---

## 功能

- 多源 RSS 抓取（36氪、量子位、虎嗅、InfoQ 等）
- HTML 清洗 + 内容优化（适配微信格式）
- 自动下载/生成封面图
- 外链图片替换为微信 CDN URL
- 草稿箱自动创建
- 定时调度（可配置间隔和时间段）
- 去重机制（同一文章不重复推送）
- wenyan-cli 排版引擎（可选）

---

## 适合谁 / 不适合谁

### ✅ 适合

- 个人运营 AI/科技/效率类公众号
- 想把优质 RSS 内容自动转成草稿的运营者
- 每天/定期需要推送但不想手动整理内容的创作者
- 有微信订阅号或服务号（已认证或未认证均可）

### ❌ 不适合

- 需要高质量原创内容的账号（RSS 内容需人工把关再发）
- 已经有完整 CMS 和工作流的团队（非个人场景）
- 没有微信公众平台账号（mp.weixin.qq.com）

---

## 第一次成功是什么样

### Step 1：配置完成后，先试运行

```bash
python main.py --dry
```

**预期输出：**
```
试运行模式 - 不创建草稿
抓取到若干篇文章
--- 某篇文章 ---
  来源: 36氪 | 标签: AI/科技
  链接: https://...
  摘要: ...
```

`--dry` 只验证抓取和清洗链路，不会创建草稿，也不要求先配置公众号凭证。

### Step 2：登录 mp.weixin.qq.com 草稿箱

把 `.env` 里的 `WECHAT_APPID` / `WECHAT_APPSECRET` 配好后，运行：

```bash
python main.py --once
```

登录后看到草稿列表里有文章即为成功。点击预览确认：
- 封面图是否正常显示
- 正文内容是否清晰可读
- 摘要是否被正确截断（未认证账号约 58 字节）

### Step 3：手动点击「群发」

草稿创建成功并不意味着发布成功。微信订阅号每月只能群发 **4 次**，草稿箱不限量，建议集中时间手动群发。

---

## 安装

```bash
# 克隆仓库
git clone https://github.com/timeyour/wechat-auto-push-lib.git
cd wechat-auto-push-lib

# 创建虚拟环境（推荐）
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 可选：wenyan-cli 排版引擎（Phase 5 排版发布需要）
npm install -g @wenyan-md/cli
# 或装到当前仓库
# npm install @wenyan-md/cli

# 配置（推荐 .env）
cp .env.example .env    # 编辑填入 AppID / AppSecret
```

仓库已自带 `config.py`，会自动读取 `.env`。`config.example.py` 只保留作字段示例。

---

## 配置

编辑 `.env`，填入微信公众号凭证：

凭证获取：微信公众平台 → 设置 → 基本配置 → AppID / AppSecret

如果你想改 RSS 源、抓取频率、发布时间段，也可以直接编辑仓库内的 `config.py`。

---

## 使用

| 命令 | 说明 |
|------|------|
| `python main.py` | 定时模式（每 6 小时自动运行） |
| `python main.py --once` | 立即执行一次 |
| `python main.py --dry` | 试运行（只抓取，不创建草稿） |
| `python main.py --list` | 查看草稿箱现有内容 |

---

## 工作流

```
RSS 多源抓取
    ↓
内容清洗（BeautifulSoup + readability）
    ↓
关键词/中文过滤（可配置）
    ↓
自动生成/下载封面图
    ↓
外链图片 → 微信 CDN URL
    ↓
创建草稿箱草稿
    ↓
mp.weixin.qq.com 草稿箱（手动群发）
```

---

## 目录结构

```
.
├── wechat_api/              # 微信 API（Token管理、图片上传、草稿创建）
│   └── publisher.py         # 草稿箱创建 + 图片上传
├── rss_sources/             # RSS 抓取模块
├── content_processor/       # HTML 清洗、图片处理、摘要提取
├── corpus-playbook/         # 语料库配置（选题/风格学习），可选
├── wechat_v2.py             # 可选的本地桌面微信辅助脚本（不属于主流程）
├── wenyan_render.mjs        # wenyan-cli 排版引擎（可选）
├── wenyan_typesetter.py     # wenyan Python 包装
├── img_fallback.py          # 封面图降级生成
├── compliance_check.py      # 16项合规检查（命令行工具）
├── add_images.py            # HTML 内嵌 Base64 图片处理
├── theme_select.mjs        # 主题选择器（wenyan 配套）
├── theme_config.py         # 主题配置文件
├── scheduler.py             # 定时调度逻辑
├── main.py                  # 入口（定时/单次/dry-run 三种模式）
├── .env.example             # 环境变量模板（推荐）
├── config.py                # 默认配置（开箱读取 .env）
├── config.example.py        # 配置字段示例
├── requirements.txt
└── README.md
```

---

## 注意事项

- 微信订阅号每月只能群发**4次**，草稿箱不限量
- 未认证订阅号摘要限制约 **58 字节**，会自动截断
- 封面图不超过 **2MB**，建议 900×383 像素（2.35:1）
- 草稿创建后需登录 mp.weixin.qq.com 手动点击「群发」
- `wechat_v2.py` 只是本地桌面自动化示例；若要使用，请额外安装 `pyautogui` 和 `pyperclip`

---

## License

MIT
