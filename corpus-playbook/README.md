# Corpus Playbook - 语料学习 + 写作手册

放历史文章 → 点选话题 → 生成专属写作手册 → 配图 → 发布

## 目录结构

```
corpus-playbook/
├── topic-gallery.html   # 30话题点选画廊（浏览器打开）
├── corpus-manager.html  # 历史文章语料库管理器
├── monitor.html         # 热点监控面板（5个数据源）
├── build-playbook.py    # 生成专属写作手册
├── learn-revision.py    # 改稿反馈学习（积累5条→playbook自动更新）
├── topics.json          # 30个话题数据（与HTML同步）
├── corpus/              # 历史文章（.md / .txt）
├── lessons/             # 改稿反馈记录（JSON）
└── playbooks/           # 生成的写作手册（按话题ID命名）
```

## 热点监控工具

| 工具 | 地址 | 用途 |
|------|------|------|
| **WeWrite** | github.com/oaker-io/wewrite | 全流程AI写作Skill（1.1k Stars） |
| **低粉爆文** | newrank.cn/hotInfo?platform=weixin | 小号爆文追踪，找信息差 |
| **今日热榜** | tophub.today | 100+平台实时热榜聚合 |
| **推特起爆** | sopilot.net/zh/hot-tweets | 推特起爆帖监控，RSS: sopilot.net/rss/hottweets |
| **NewsNow** | newsnow.busiyi.world | 开源新闻聚合，PWA支持 |

打开监控面板：`corpus-playbook/monitor.html`

## 操作流程

```
Step 1: 放入历史文章
  → 把10-30篇最好的文章放进 corpus-playbook/corpus/

Step 2: 打开话题画廊
  → 浏览器打开 corpus-playbook/topic-gallery.html
  → 点选今天要写的话题

Step 3: 生成专属写作手册
  → 复制底部命令，终端运行：
    python build-playbook.py 1   （假设选了「AI工具实测」）

Step 4: 写作时引用 Playbook
  → 告诉AI：「请参考 corpus-playbook/playbooks/01_AI工具实测.md
     写一篇XXX的公众号文章」

Step 5: 改稿迭代（可选）
  → 手动改了AI稿后：
    python learn-revision.py add ai_draft.md human_published.md
  → 积累5条 → 重新生成 playbook → AI越来越像你的风格
```

## 30话题分类

| 分类 | 话题数 | 代表话题 |
|------|--------|---------|
| 工具 | 5个 | AI工具实测、GitHub热榜解读、效率技巧、Prompt工程、API接入 |
| 洞察 | 5个 | AI行业观察、产品分析、技术原理、创业思考、行业预测 |
| 教程 | 6个 | 新手入门、工具对比、自动化流程、本地部署、API接入、安全配置 |
| 观点 | 4个 | 观点输出、避坑指南、行业预测、冷知识 |
| 故事 | 4个 | 个人故事、案例拆解、幕后花絮、失败复盘 |
| 合集 | 4个 | 资源合集、Prompt合集、书单推荐、工具清单 |
| 热点 | 2个 | 热点追踪、选题参考 |
