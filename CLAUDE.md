# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

## 项目概览

SmartTodo 是一个带 AI 助手能力的个人待办事项管理器。后端为 Python Flask + SQLAlchemy + SQLite，前端为 Vue 3 + TypeScript + Vite。通过 Docker 部署。

## 开发命令

### 后端 (Python)

```bash
cd backend

# 激活虚拟环境（所有 Python 命令前必须执行）
source venv/bin/activate

# 安装依赖（在 venv 内执行）
pip install -r requirements.txt
pip install pytest pytest-cov

# 启动开发服务器（端口 4231）
PYTHONPATH=. python run.py

# 运行全部测试（带覆盖率）
PYTHONPATH=. pytest --cov=./ --cov-report=html

# 运行单个测试文件
PYTHONPATH=. pytest app/tests/services/item_test.py

# Lint/格式化 (ruff)
ruff check .
ruff format .
```

### 前端 (Vue 3)

```bash
cd web

npm install
npm run dev        # Vite 开发服务器，将 /api 代理到 localhost:4231
npm run type-check # 类型检查
npm run lint       # Lint
npm run format     # 格式化
npm run build      # 生产构建
```

### Docker

```bash
docker build . --file docker/Dockerfile --tag ghcr.io/lizec123/smart-todo
```

## 架构

### 后端 (`backend/`)

**入口：** `run.py` — 通过 `create_app()` 创建 Flask 应用，运行在 4231 端口。`@app.teardown_appcontext` 在请求结束时提交或回滚 session。

**`app/__init__.py`** 是组合根。初始化数据库引擎（SQLite，文件 `data/data.db`），创建线程局部 `scoped_session`（即 `db`），实例化所有 service 单例，注册 Flask 蓝图，启动 `TaskManager` 定时任务。

**`app/models/`** — SQLAlchemy ORM 模型，全部继承自 `Base`。主要模型：
- `Item` — 核心待办实体，字段包括类型（single/file/note）、截止日期、优先级、番茄钟状态、可重复性、父任务（便签子任务）
- `History` — AI 助手聊天记录，支持转换为 OpenAI 消息格式。`tool_call_list_json` 存储模型请求的工具调用，`tool_call_id` 关联工具返回结果
- `MemoryDetail` — 追加式长期记忆，按类型分类（角色设定、用户偏好、近期话题、日记、固化设定/偏好、里程碑、流言蜚语）
- `EventLog` — 记录任务进度事件，供 AI 上下文注入
- `CheckinState` — 打卡统计（总次数、连续天数、补卡次数、21 天挑战进度）
- `Credit`/`CreditLog` — 积分系统
- `WeightLog` — 体重记录，同时作为打卡数据源

**`app/services/`** — 业务逻辑，全部在 `__init__.py` 中实例化为单例：
- `ItemManager` — 待办事项 CRUD、优先级计算、任务状态转换、垃圾回收
- `AssistantManager`（`llm_manager.py`，约 53KB）— AI 助手主控：聊天、多角色管理、记忆压缩、流言蜚语传播、上下文注入、工具调用编排
- `AssistantHistoryManager`（`llm_manager.py`）— History 表的 DB 操作层，管理聊天记录的增删查
- `AssistantMemoryManager`（`llm_manager.py`）— MemoryDetail 表的 DB 操作层，管理长期记忆的读写和压缩
- `TomatoManager` / `TomatoRecordManager` — 番茄钟状态和记录
- `CheckinManager` — 每日打卡/连续天数统计，支持可扩展的打卡数据源
- `ConfigManager` — 读取 `config/default.json`（如有 `config.json` 则优先），提供 LLM 凭证和用户信息
- `OpInterpreter` — 管理员指令解释器（`func` 前缀的系统命令）
- `CreditManager` — 积分系统
- `TaskManager` — 基于 `schedule` 库的定时任务线程，执行每日任务（垃圾回收、任务重置、记忆压缩）

**分层设计约束：** `llm_manager.py` 中的 `AssistantManager` 不应直接操作 History 表的 DB 查询。所有 History 的 CRUD 必须通过 `AssistantHistoryManager` 的方法完成，`AssistantManager` 仅负责编排和格式化。同理，`MemoryDetail` 的操作通过 `AssistantMemoryManager`。

**`app/views/`** — Flask 蓝图，按领域划分。每个路由使用 `@authority_check()` 装饰器，从 Flask session 提取 `owner` 并注入到处理函数，未登录则返回 401。

**`app/tools/`** — 工具模块：
- `llm.py` — `LLMClient` 封装 OpenAI SDK，支持流式输出、工具调用和 thinking/reasoning 内容提取
- `redis.py` — `MemoryCache`，基于内存的线程安全 TTL 缓存（名字叫 redis 但并非 Redis）
- `time.py` — 日期时间工具（`now()`、`today()`、截止日期解析）
- `exception.py` — 自定义异常层次
- `web.py` — URL 标题提取，用于网页书签
- `file.py` — 文件上传/下载管理

**`app/template/`** — LLM 提示词和 OpenAI 函数定义：
- `prompt.py` — 助手模式、扮演模式、记忆压缩、流言蜚语传播的系统提示词
- `tools.py` — `CreatItemTool`、`AnyQueryTool`、`GetDeadlineItemTool` 函数定义

### 前端 (`web/`)

**Vue 3 + Pinia + Vue Router + TypeScript + Vite。** Vite 开发服务器将 `/api` 和 `/admin` 代理到 `localhost:4231`。

**页面**（`src/view/`）：`Index`、`TodoPage`、`TomatoPage`、`Assistant`、`Checkin`、`SummaryPage`、`LoginPage`，以及 `me/` 下的子页面。

**组件目录**（`src/components/`）：`item/`（待办项组件）、`submit/`、`footer/`、`editor/`（便签富文本）、`timeline/`、`tomato/`、`analysis/`、`eventline/`。

**状态管理**（`src/stores/`）：Pinia store（`items.ts`）。

**主要依赖：** axios（401 拦截器自动跳转登录页）、chart.js、dayjs、font-awesome。

### 关键设计模式

- **单例 Service：** 所有 service 对象在 `app/__init__.py` 中创建一次，由 views 直接导入使用。无 DI 容器。
- **Session 认证：** Flask session 在登录后存储 `username` 和 `role`。`authority_check` 装饰器校验认证并将 `owner` 注入路由处理函数。
- **DB 会话管理：** `db` 是 `scoped_session`。`run.py` 在请求结束时无异常则提交，有异常则回滚。
- **分层架构：** `AssistantManager` 不直接操作 History/MemoryDetail 的 DB 查询，所有 DB 操作通过 `AssistantHistoryManager` 和 `AssistantMemoryManager` 完成。
- **定时任务：** `TaskManager` 每日定时执行。非 PROD 环境跳过 LLM 相关定时任务（由 `ENV` 环境变量控制）。
- **测试数据隔离：** `do_test.sh` 先移走 `data/` 目录再运行测试，确保测试不污染真实数据。测试使用真实的 SQLite 数据库（非 mock）。

## 配置

- `config/default.json` — 默认配置，包含测试用户（`admin`/`user`，密码均为 `123456`）
- `config/config.json` — 如存在则覆盖默认配置（用于生产环境）
- LLM 配置位于 `LLM_INFO`，包含 `BASE_URL`、`API_KEY`、`MODEL_NAME`。可选 `LLM_TOOL_INFO` 可指定更便宜的模型处理工具类调用
- `ENV=PROD` 环境变量启用 LLM 相关定时任务
