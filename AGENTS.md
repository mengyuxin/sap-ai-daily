# AGENTS.md — sap-ai-daily

## 1. 项目目标

本项目名为 `sap-ai-daily`。

目标是构建一个可由 GitHub 托管、由 Codex 持续维护的自动化“AI・SAP 科技早报”系统。

系统最终应能够：

1. 定时收集 AI、SAP、Cloud、Enterprise Tech 等领域的公开新闻；
2. 对新闻进行去重、筛选、排序和事实核验；
3. 生成适合新浪微博发布的中文“AI・SAP 科技早报”；
4. 支持生成每日封面图或摘要图；
5. 支持定时发布到微博；
6. 保存每次运行的来源、生成结果、发布结果和错误日志；
7. 可在 GitHub Actions 中无人值守运行。

当前阶段的重点是：**先完成可靠、可测试、可 Dry Run 的系统，不要直接对真实微博账号发布内容。**

---

## 2. 工作原则

Codex 在本仓库中工作时必须遵守以下原则：

- 优先保证准确性，不追求“新闻数量”。
- 不得编造新闻、来源、发布日期、公司声明或链接。
- 所有新闻必须能追溯到原始来源。
- 优先使用官方来源和高可信媒体。
- 同一事件的多篇报道应合并，而不是重复发布。
- 对未经官方确认的消息必须降低优先级，必要时排除。
- SAP 相关新闻应尽可能引用 SAP 官方 News Center、SAP Community、SAP Help、SAP Support 等可信来源。
- AI 相关新闻优先引用 OpenAI、Anthropic、Google、Microsoft、NVIDIA、AWS 等官方来源，以及 Reuters 等高可信媒体。
- 任何“发布”动作都必须支持 Dry Run。
- 在没有明确配置真实发布凭据前，不得向微博或其他社交平台发送真实内容。
- 不得把 API Key、Token、Cookie、账号、密码写入 Git 仓库。
- 所有 Secret 必须通过环境变量或 GitHub Actions Secrets 注入。
- 对外部网站的抓取必须遵守其公开访问方式、robots/ToS 和速率限制。
- 修改代码后必须运行测试。
- 不为了“看起来完整”而添加没有实际使用的复杂框架。

---

## 3. 推荐技术栈

默认使用：

- Python 3.12+
- `uv` 或 `pip` 管理依赖
- `pytest` 测试
- `ruff` 进行 lint / format
- `httpx` 进行 HTTP 请求
- `feedparser` 处理 RSS/Atom
- `pydantic` 管理数据模型和配置
- GitHub Actions 负责定时运行
- SQLite 或 JSON Lines 作为第一阶段运行记录存储

如无充分理由，不要引入重量级数据库、消息队列、Web Framework。

---

## 4. 建议目录结构

```text
sap-ai-daily/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── config/
│   ├── sources.yaml
│   └── settings.yaml
├── prompts/
│   ├── select_news.md
│   ├── summarize_news.md
│   └── write_weibo.md
├── src/
│   └── sap_ai_daily/
│       ├── __init__.py
│       ├── config.py
│       ├── models.py
│       ├── fetch/
│       │   ├── base.py
│       │   ├── rss.py
│       │   └── web.py
│       ├── process/
│       │   ├── normalize.py
│       │   ├── deduplicate.py
│       │   ├── rank.py
│       │   └── verify.py
│       ├── llm/
│       │   ├── client.py
│       │   ├── select.py
│       │   └── summarize.py
│       ├── render/
│       │   ├── weibo.py
│       │   └── cover.py
│       ├── publish/
│       │   ├── base.py
│       │   ├── dry_run.py
│       │   └── weibo.py
│       ├── storage/
│       │   └── history.py
│       └── cli.py
├── tests/
│   ├── test_deduplicate.py
│   ├── test_rank.py
│   ├── test_render_weibo.py
│   └── test_dry_run.py
├── data/
│   └── .gitkeep
├── output/
│   └── .gitkeep
└── .github/
    └── workflows/
        ├── test.yml
        └── daily.yml
```

可以根据实际实现适当调整，但应保持模块职责清晰。

---

## 5. 新闻分类

第一阶段至少支持以下分类：

### SAP

包括但不限于：

- SAP S/4HANA
- SAP BTP
- SAP Business AI
- Joule
- SAP Cloud ERP
- SAP Datasphere
- SAP Analytics Cloud
- SAP Signavio
- SAP Integration Suite
- SAP Cloud ALM
- SAP Security / Support / Upgrade
- SAP 与 AI / Hyperscaler 合作

### AI

包括但不限于：

- OpenAI
- Anthropic
- Google DeepMind / Gemini
- Microsoft AI / Copilot
- NVIDIA
- Meta AI
- AWS AI
- 企业级 Agent
- LLM / Coding Agent
- AI Infra

### Enterprise Tech

包括但不限于：

- Cloud
- Datacenter
- Cybersecurity
- Enterprise Software
- Developer Tools

新闻比例不要写死，但默认生成结果应突出：

1. AI
2. SAP
3. 企业科技

---

## 6. Source 配置

新闻源不得硬编码在业务逻辑中。

使用 `config/sources.yaml` 管理，例如：

```yaml
sources:
  - id: sap-news
    name: SAP News Center
    category: sap
    type: rss
    url: "..."
    priority: 100

  - id: openai-news
    name: OpenAI
    category: ai
    type: rss
    url: "..."
    priority: 100
```

每个 source 至少包含：

- `id`
- `name`
- `category`
- `type`
- `url`
- `priority`
- `enabled`

如某来源没有稳定 RSS，不要擅自使用脆弱的 HTML selector 抓取；应优先寻找官方 RSS/API，或先保留为待实现 source。

---

## 7. 数据模型

至少定义以下实体：

### NewsItem

建议字段：

```text
id
title
url
source_id
source_name
category
published_at
fetched_at
summary_raw
content_raw
language
canonical_url
fingerprint
```

### SelectedNewsItem

除原始字段外，增加：

```text
importance_score
relevance_score
confidence_score
reason
verified
```

### DailyBrief

至少包含：

```text
date
headline
items
editor_note
hashtags
source_count
generated_at
```

---

## 8. 去重规则

必须实现新闻去重。

至少考虑：

- canonical URL
- 标题标准化
- 相似标题
- 同一新闻事件来自多个媒体
- 同一官方公告被转载

去重逻辑不能只依赖完全相同标题。

第一阶段可以使用：

- normalized title
- token similarity
- URL canonicalization

后续再考虑 embedding。

---

## 9. 新闻筛选和排序

排序建议综合：

```text
可信来源
+ 新鲜度
+ SAP/AI相关度
+ 行业影响力
+ 对企业用户的价值
+ 对 SAP 顾问的价值
```

减少：

```text
营销软文
重复新闻
纯融资八卦
没有实际变化的产品宣传
来源不明的爆料
标题党
```

每天最终建议选择 5～8 条。

---

## 10. LLM 使用原则

LLM 负责：

- 分类
- 合并同一事件
- 判断重要性
- 摘要
- 改写为微博文案

LLM 不负责创造事实。

Prompt 必须明确：

- 不得补充来源中没有的信息
- 不确定时必须降低置信度
- 数字、日期、产品名、公司名必须忠实于来源
- 不得伪造引用

LLM 返回结果尽量使用结构化 JSON，并使用 Pydantic 校验。

---

## 11. 微博内容格式

默认风格：

```text
【AI・SAP 科技早报｜YYYY.MM.DD】

① 标题
一句简要说明。

② 标题
一句简要说明。

③ ...

今日关注：
一句编辑观点。

#AI #SAP #科技早报
```

要求：

- 中文自然，不要有明显 AI 腔。
- 标题简洁。
- 不使用夸张的“震撼”“炸裂”“重磅”等词，除非原始事实确实支持。
- 不直接复制新闻原标题的大段文字。
- 避免长篇评论。
- 每条新闻保留来源信息到结构化数据中。
- 微博正文是否附链接应通过配置控制。
- 应支持长度检查。
- 超长时优先压缩摘要，而不是简单截断。

---

## 12. 时间规则

项目统一以：

```text
Asia/Shanghai
```

作为业务时区。

最终目标发布时间：

```text
每天 00:00
```

但 GitHub Actions 使用 UTC，因此 workflow 必须明确处理时区，不允许靠开发者心算长期维护。

代码中使用 timezone-aware datetime。

不要使用 naive datetime。

---

## 13. 发布设计

发布层必须使用 Adapter 模式。

定义统一接口，例如：

```python
class Publisher:
    def publish(self, brief: DailyBrief) -> PublishResult: ...
```

至少实现：

```text
DryRunPublisher
WeiboPublisher
```

### DryRunPublisher

默认启用。

行为：

- 不发送任何网络发布请求
- 将最终微博内容写入 `output/`
- 输出模拟发布结果

### WeiboPublisher

第一阶段只完成接口和配置框架。

只有在同时满足以下条件时才能真实发布：

```text
PUBLISH_ENABLED=true
WEIBO_* 凭据完整
显式选择 production publisher
```

缺少任何条件时必须失败关闭（fail closed），自动退回 Dry Run 或终止，不允许误发。

---

## 14. 微博接口注意事项

不要假设某个微博 API、CLI 或第三方 SDK 一定长期可用。

实现前应：

1. 查阅新浪微博当前官方开放平台文档；
2. 明确当前账号类型是否具有发布权限；
3. 明确 OAuth / Token 生命周期；
4. 明确文本、图片、频率等限制；
5. 将微博具体实现隔离在 `publish/weibo.py`；
6. 不让其影响新闻生成核心逻辑。

如果没有可用的官方发布接口：

- 保持 Dry Run；
- 生成可人工发布的文本和图片；
- 在 README 中记录限制；
- 不使用未经用户明确批准的浏览器模拟登录方案。

---

## 15. 配图

第一阶段可先实现固定模板封面，不要求 AI 图片生成。

建议输出：

```text
AI・SAP 科技早报
YYYY.MM.DD
TOP 3
```

封面生成应：

- 不使用受版权保护的新闻图片作为默认素材；
- 可使用纯色、渐变、几何背景；
- 字体必须有 fallback；
- 无字体时不能导致整个 pipeline 失败；
- 输出 PNG；
- 配图失败时仍允许生成纯文本早报。

---

## 16. 历史记录

每次运行必须保存：

```text
运行日期
抓取来源
抓取新闻数量
去重后数量
最终选择数量
最终微博正文
来源 URL
生成时间
发布状态
发布 ID（如果有）
错误信息
```

建议保存为：

```text
data/YYYY-MM-DD.json
output/YYYY-MM-DD.md
```

不要提交大量运行数据到 Git；默认通过 `.gitignore` 忽略实际运行数据，仅保留示例。

---

## 17. GitHub Actions

至少准备两个 workflow。

### test.yml

触发：

- push
- pull_request

运行：

```text
ruff check
ruff format --check
pytest
```

### daily.yml

第一阶段：

- 支持 `workflow_dispatch`
- 支持 schedule
- 默认 Dry Run
- 上传当日生成物为 artifact

在用户确认真实发布前：

```text
PUBLISH_ENABLED=false
```

不得修改为 true。

---

## 18. 环境变量

使用 `.env.example`，至少预留：

```dotenv
APP_ENV=development
TZ=Asia/Shanghai
PUBLISH_ENABLED=false

LLM_PROVIDER=
LLM_API_KEY=
LLM_MODEL=

WEIBO_CLIENT_ID=
WEIBO_CLIENT_SECRET=
WEIBO_ACCESS_TOKEN=
```

实际 `.env` 必须在 `.gitignore`。

不得输出 Secret 到日志。

---

## 19. CLI

项目应提供简单 CLI，例如：

```bash
python -m sap_ai_daily fetch
python -m sap_ai_daily build
python -m sap_ai_daily run --dry-run
python -m sap_ai_daily run --date 2026-09-12 --dry-run
```

最终目标：

```bash
python -m sap_ai_daily run
```

即可执行完整 pipeline。

---

## 20. 测试要求

至少覆盖：

- 新闻标题 normalization
- URL normalization
- 去重
- 排序
- 微博渲染
- 长度控制
- Dry Run
- 配置读取
- 缺失 Secret 时禁止真实发布
- 时间区域处理

测试不得真实调用微博发布接口。

对外部 HTTP 请求使用 mock。

---

## 21. 日志

使用 Python logging。

日志至少包括：

```text
run_id
stage
source
count
duration
status
error
```

不要打印：

```text
API key
access token
cookie
完整 authorization header
```

---

## 22. 错误处理

要求：

- 单一新闻源失败时，不应导致整个任务失败；
- 所有核心来源都失败时，应终止发布；
- LLM 返回无效 JSON 时应重试有限次数；
- 新闻不足时宁可少发，不要编造；
- 配图失败时允许降级成纯文本；
- 发布失败必须记录，且不得重复发布同一 DailyBrief。

---

## 23. 幂等性

同一日期的任务重复执行时必须避免重复发布。

至少使用：

```text
date + content_hash
```

判断是否已发布。

如果存在成功发布记录：

- 默认禁止再次发布；
- 只有显式 `--force` 才允许重新生成/发布；
- `--force` 也必须遵守 `PUBLISH_ENABLED`。

---

## 24. README 要求

README 至少包含：

1. 项目简介
2. 架构图
3. 安装方法
4. 本地运行
5. Dry Run
6. GitHub Actions
7. 配置新闻源
8. 配置 LLM
9. 微博发布说明
10. Secret 管理
11. 测试方法
12. 当前限制
13. Roadmap

README 使用中文为主。

---

## 25. 开发阶段

### Phase 1 — MVP

先完成：

```text
RSS读取
→ 标准化
→ 去重
→ 基础排序
→ 生成 DailyBrief
→ 微博文本
→ Dry Run
→ 测试
```

不做真实微博发布。

### Phase 2 — LLM

增加：

```text
新闻重要度判断
摘要
编辑点评
结构化输出
```

### Phase 3 — GitHub Actions

增加：

```text
daily workflow
artifact
运行记录
```

### Phase 4 — Weibo

确认官方发布能力后：

```text
OAuth
Publisher
图片上传
真实发布
幂等控制
```

### Phase 5 — Quality

增加：

```text
更强去重
事实核验
来源评分
历史数据
每日封面
失败告警
```

不要跳过 Phase 1 直接实现所有功能。

---

## 26. 代码风格

- Python 类型提示必须完整。
- 函数保持短小。
- I/O 与业务逻辑分离。
- 不使用全局可变状态。
- 使用 dataclass 或 Pydantic Model 表达结构化数据。
- 配置与代码分离。
- 避免 magic number。
- 公共方法添加 docstring。
- 注释解释“为什么”，不要解释明显的“做什么”。

---

## 27. 禁止事项

禁止：

- 提交 Secret
- 硬编码真实微博账号信息
- 未经确认直接发布
- 编造新闻
- 编造来源链接
- 直接复制整篇新闻
- 大量抓取受限制网站
- 用 Selenium 模拟微博登录作为默认方案
- 为 MVP 引入 Kubernetes、Redis、Celery 等过重组件
- 在没有测试的情况下修改发布逻辑
- 因单个 source 抓取失败而生成虚假内容

---

## 28. Codex 每次工作的流程

每次接受任务后：

1. 阅读 `AGENTS.md`；
2. 阅读相关现有代码；
3. 查看 `git status`；
4. 用最小改动完成任务；
5. 更新或增加测试；
6. 运行：

```bash
ruff check .
ruff format --check .
pytest
```

7. 如改动影响用户使用方式，同步更新 README；
8. 再次检查 `git diff`；
9. 确认没有 Secret、临时文件、调试代码；
10. 清楚说明：
   - 改了什么；
   - 为什么这样改；
   - 测试结果；
   - 尚未解决的问题。

---

## 29. 第一项开发任务

如果仓库目前为空，Codex 应从 Phase 1 开始。

第一轮请完成：

1. 初始化 Python 项目；
2. 创建推荐目录结构；
3. 建立 `NewsItem`、`DailyBrief` 等数据模型；
4. 实现 RSS Source Adapter；
5. 实现基本 normalize + deduplicate；
6. 实现简单 rule-based ranking；
7. 实现微博文本 renderer；
8. 实现 DryRunPublisher；
9. 增加 `config/sources.yaml` 示例；
10. 增加 `.env.example`；
11. 增加 CLI：
    ```bash
    python -m sap_ai_daily run --dry-run
    ```
12. 增加 pytest；
13. 增加 GitHub Actions `test.yml`；
14. 编写中文 README；
15. 不实现真实微博发布。

验收标准：

```text
clone repository
→ install dependencies
→ run tests
→ run dry-run
→ output/YYYY-MM-DD.md 生成
```

整个流程不需要任何真实账号或 Secret。

---

## 30. 最终设计原则

这个项目的优先级顺序永远是：

```text
准确
> 可追溯
> 稳定
> 可测试
> 自动化
> 发布速度
```

宁可当天少一条新闻，也不要发布一条错误新闻。
