# 微信公众号自动推送工具

**RSS 抓取 → 内容清洗 → 微信素材上传 → 草稿箱**，全自动、半自动、手动三种模式。

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

# 复制配置
copy config.example.py config.py
# Linux/macOS
cp config.example.py config.py
```

---

## 配置

编辑 `config.py`，填入微信公众号凭证：

```python
WECHAT_APPID = "your_appid_here"
WECHAT_APPSECRET = "your_appsecret_here"
```

或在 `.env` 文件中配置：

```env
WECHAT_APPID=your_appid_here
WECHAT_APPSECRET=your_appsecret_here
```

凭证获取：微信公众平台 → 设置 → 基本配置 → AppID / AppSecret

---

## 使用

### 定时模式（每6小时自动运行）
```bash
python main.py
```

### 立即执行一次
```bash
python main.py --once
```

### 试运行（只抓取，不发布）
```bash
python main.py --dry
```

### 查看草稿箱
```bash
python main.py --list
```

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
├── rss_sources/             # RSS 抓取模块
├── content_processor/       # HTML 清洗、图片处理、摘要提取
├── wenyan_typesetter.py     # wenyan-cli 排版引擎（可选）
├── scheduler.py             # 定时调度逻辑
├── config.py                # 配置文件（需自行创建）
├── config.example.py        # 配置模板
├── requirements.txt
└── README.md
```

---

## 注意事项

- 微信订阅号每月只能群发**4次**，草稿箱不限量
- 未认证订阅号摘要限制约 **58 字节**，会自动截断
- 封面图不超过 **2MB**，建议 900×383 像素（2.35:1）
- 草稿创建后需登录 mp.weixin.qq.com 手动点击「群发」

---

## 许可证

MIT
