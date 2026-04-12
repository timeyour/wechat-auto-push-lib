# wechat-auto-push-lib 项目指南

> 基于 Karpathy AI 编程 4 大原则，为 AI 编码助手提供项目特定规范。

---

## 四大核心原则

### 1. Think Before Coding（编码前思考）
- 明确陈述假设——不确定时**主动提问而非猜测**
- 调用微信 API 前验证参数是否正确
- 困惑时停止，说出不清楚的地方并请求澄清

### 2. Simplicity First（简洁优先）
- **不添加超出需求的功能**
- 单次使用的代码不创建抽象
- 不添加未请求的"灵活性"或"可配置性"
- 如果 100 行可以写成 30 行，就重写
- **判断标准**：如果高级工程师认为这太复杂了，就简化

### 3. Surgical Changes（精准改动）
- 编辑现有代码时**只改必要的部分**
- 不"改进"相邻代码、注释或格式
- 不重构没坏的东西
- 匹配现有风格，即使你会用不同方式
- **每行改动的代码都应能追溯到用户的请求**

### 4. Goal-Driven Execution（目标驱动执行）
- 将命令式任务转化为**可验证的目标**
- 示例：
  - "添加 RSS 源" → "配置新 RSS 源，能抓取 3 篇且格式正确"
  - "修复 bug" → "编写能复现 bug 的测试，然后让测试通过"
  - "重构 X" → "确保重构前后测试都通过"

---

## 技术栈

- **Python 3.10+**
- 核心库：requests, BeautifulSoup, feedparser, readability, wechatpy, APScheduler
- 可选：Pillow (图片处理), 飞书 SDK

---

## 代码规范

### 命名规范
- 函数名：`snake_case`（如 `fetch_rss_feed`）
- 类名：`PascalCase`（如 `WeChatPublisher`）
- 常量：`UPPER_SNAKE_CASE`（如 `MAX_THUMB_SIZE_BYTES`）

### 函数规范
- 所有公开函数必须添加 **Type Hints**
- 单个函数不超过 **50 行**（如超过，考虑拆分）
- 必须包含 **docstring**（说明参数和返回值）

### 类型注解
```python
# Good
def process_article(publisher: WeChatPublisher, article: Article) -> bool:
    """处理单篇文章"""
    ...

# Bad
def process_article(publisher, article):
    ...
```

### 魔法数字
- 所有魔法数字必须定义在 `config.py`
- 禁止在业务代码中出现硬编码数字

```python
# Bad
if image_path.stat().st_size > 2 * 1024 * 1024:

# Good (config.py)
MAX_THUMB_SIZE_BYTES = 2 * 1024 * 1024

# 业务代码
if image_path.stat().st_size > MAX_THUMB_SIZE_BYTES:
```

---

## 测试要求

### 目录结构
```
tests/
├── __init__.py
├── test_content_processor.py
├── test_publisher.py
├── test_fetcher.py
└── fixtures/
    ├── sample_article.html
    └── sample_rss.xml
```

### 测试原则
- 新增函数必须附带单元测试
- 微信 API 调用使用 `unittest.mock` 模拟
- 测试覆盖率目标：核心模块 ≥ 80%

### 测试示例
```python
import pytest
from unittest.mock import patch, MagicMock

class TestCleanHtml:
    def test_remove_script_tags(self):
        html = '<script>alert("xss")</script><p>Hello</p>'
        result = clean_html(html)
        assert '<script>' not in result
        assert '<p>Hello</p>' in result

    @patch('requests.get')
    def test_fetch_full_content(self, mock_get):
        mock_get.return_value.text = '<html><body><p>Test content</p></body></html>'
        result = _fetch_full_content('https://example.com')
        assert 'Test content' in result
```

---

## 模块职责

| 模块 | 职责 | 不应做的事 |
|-----|------|----------|
| `rss_sources/` | RSS 抓取、去重、过滤 | 不做内容清洗 |
| `content_processor/` | HTML 清洗、图片处理、封面生成 | 不调用微信 API |
| `wechat_api/` | 微信 API 封装、Token 管理 | 不处理业务逻辑 |
| `scheduler.py` | 调度编排、流水线协调 | 不直接操作 HTML |
| `config.py` | 所有配置常量 | 不包含业务逻辑 |

---

## 跨平台兼容性

### 字体路径
使用 `_get_font_path()` 函数，**不要硬编码** Windows 路径。

### 路径处理
- 使用 `pathlib.Path` 而非字符串拼接
- `DATA_DIR`、`COVER_CACHE` 等使用 `Path(__file__).parent` 相对定位

---

## 错误处理

### 自定义异常
使用 `exceptions.py` 中的异常类：

```python
from exceptions import WeChatPushError, TokenExpiredError

try:
    publisher.create_draft(...)
except TokenExpiredError:
    token_manager._refresh_token()
except WeChatPushError as e:
    logger.error(f"发布失败: {e}")
```

### 日志规范
```python
logger = logging.getLogger(__name__)

logger.debug()   # 详细调试信息
logger.info()    # 正常操作信息（如抓取成功、上传成功）
logger.warning() # 可恢复的错误（如图片替换失败）
logger.error()   # 不可恢复的错误（如 API 调用失败）
```

---

## Git 提交规范

### Commit Message 格式
```
<type>(<scope>): <subject>

Types:
- feat: 新功能
- fix: Bug 修复
- refactor: 重构
- test: 测试相关
- docs: 文档更新
- chore: 构建/工具变更

Examples:
- feat(content): 添加 RSS 源过滤功能
- fix(publisher): 修复 Token 过期重试逻辑
- test(content_processor): 添加 clean_html 单元测试
```

---

## PR 审查 Checklist

提交 PR 前自查：

- [ ] 代码符合 Simplicity First 原则
- [ ] 所有公开函数有 Type Hints
- [ ] 没有魔法数字（已在 config.py 定义）
- [ ] 新增函数有单元测试
- [ ] 跨平台兼容（如涉及文件/字体）
- [ ] Commit message 符合规范
