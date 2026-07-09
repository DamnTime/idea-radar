# IdeaRadar · 点子雷达

> 每日自动采集多平台 AI 轻创业讨论，经去重、营销号过滤、LLM 可行性评分后，邮件推送高价值创业点子。

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![English](https://img.shields.io/badge/English-README-blue)](README.md)

---

## 核心流程

```
采集 (Reddit + 知乎 + RSS)
    ↓
语义去重 (SimHash, 阈值 0.85)
    ↓
营销号过滤 (关键词 + 内容特征)
    ↓
LLM 可行性评分 (0-10, 五维度加权)
    ↓
排序 → Top N → 邮件推送 (HTML)
```

## 数据源

| 源 | 方式 | 认证 |
|---|---|---|
| Reddit | `old.reddit.com` JSON API | 无需 |
| 知乎 | 热榜 + 搜索 API | 无需 |
| RSS | 任意 Atom/RSS feed | 无需 |

## 快速开始

### 前置条件

- Python 3.10+
- OpenAI 兼容 API Key（支持 DeepSeek / GLM-4 等）
- SMTP 邮箱（用于邮件推送）

### 安装与运行

```bash
# 1. 进入项目目录
cd idea-radar

# 2. 安装依赖
pip install -r requirements.txt
# 或用 uv: uv sync

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入:
#   OPENAI_API_KEY=sk-xxx
#   SMTP_HOST=smtp.gmail.com
#   SMTP_PORT=587
#   SMTP_USER=your@gmail.com
#   SMTP_PASS=your-app-password
#   EMAIL_FROM=your@gmail.com
#   EMAIL_RECIPIENTS=user@example.com

# 4. 运行
python -m src.main --hours 24 --top-n 5
```

### Docker

```bash
docker compose up --build
```

### GitHub Actions（定时自动运行）

Fork 本仓库，在 Settings → Secrets 中添加上述环境变量，`daily-push.yml` 会自动在 UTC 0:00 / 8:00 / 16:00 执行。

## 项目结构

```
idea-radar/
├── src/
│   ├── main.py                   # CLI 入口
│   ├── orchestrator.py           # 流程编排
│   ├── models.py                 # 数据模型
│   ├── scrapers/                 # 采集器
│   │   ├── reddit.py
│   │   ├── rss.py
│   │   └── zhihu.py
│   ├── processors/               # 处理器
│   │   ├── deduplicator.py       # SimHash 去重
│   │   ├── spam_filter.py        # 营销号过滤
│   │   └── scorer.py             # LLM 评分
│   └── notifiers/
│       └── email_notifier.py     # 邮件推送
├── data/config.json              # 用户配置
├── config/spam_keywords.txt      # 关键词库
├── prompts/scorer.txt            # LLM prompt
├── templates/email.html          # 邮件模板
├── Dockerfile / docker-compose.yml
└── docs/                         # 设计文档
    ├── 01-requirements.md
    ├── 02-technical-plan.md
    └── 03-skill.md
```

## 技术栈

| 层 | 技术 |
|---|---|
| 语言 | Python 3.10+ |
| 采集 | httpx (异步) |
| 去重 | SimHash + jieba |
| 评分 | OpenAI 兼容 API |
| 推送 | SMTP (HTML 邮件) |
| 部署 | Docker / GitHub Actions |

## 许可证

MIT
