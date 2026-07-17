# AstroStock 🌌📈 — MVP Monorepo

**占星股市预测系统** — 当星辰指引投资方向

> ⚠️ 免责声明：本系统仅供研究和娱乐参考，不构成任何投资建议。

## 仓库布局

```
astro-stock/
├── frontend/          # Vue 3 + TS + Vite + Tailwind v4
├── backend/           # Python FastAPI + pyswisseph
├── docker-compose.yml # Postgres + TimescaleDB + 前后端
├── docs/              # 设计文档
└── prototype/         # 交互式 HTML 原型（已完成）
```

## 快速开始

### 一键启动（Docker）

```bash
docker compose up -d          # 起 Postgres + 后端 + 前端
open http://localhost:5173    # 前端
open http://localhost:8000/docs # 后端 API 文档
```

### 本地开发（前后端分离）

```bash
# 后端
cd backend
cp .env.example .env
pip install -e .
uvicorn app.main:app --reload --port 8000

# 前端（另开终端）
cd frontend
pnpm install
pnpm dev   # → http://localhost:5173
```

## 环境要求

| 工具 | 版本 | 用途 |
|------|------|------|
| Node.js | ≥ 20 | 前端构建 |
| pnpm | ≥ 9 | 前端包管理 |
| Python | ≥ 3.10 | 后端运行 |
| Docker | ≥ 24 | 一键部署（可选） |

## 数据库与迁移（P2-5）

**dev 默认 SQLite**（零依赖，开箱即用），**生产切 Postgres + TimescaleDB**。

```bash
# dev — SQLite，init_db() 自动建表，无需 migration
cd backend && uvicorn app.main:app --reload

# 生产 — 切 Postgres（docker-compose 起 db 后）
export ASTRO_DB_URL="postgresql+psycopg://astro:astro@localhost:5432/astrostock"
cd backend && alembic upgrade head   # 跑 migration 建表
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

| env 变量 | dev 默认 | 生产 |
|---------|---------|-----|
| `ASTRO_DB_URL` | `sqlite:///./data/astrostock.db` | `postgresql+psycopg://astro:astro@db:5432/astrostock` |
| `ASTRO_JWT_SECRET` | `dev-secret-change-in-prod` | **必改**，随机长串 |
| `ASTRO_JWT_EXPIRE_MINUTES` | `1440`（1 天） | 按需 |

新增 migration（改 `app/models.py` 后）：

```bash
cd backend
# autogenerate 对比 models vs 当前 DB，产新 revision
alembic revision --autogenerate -m "add xxx table"
# 审 migrations/versions/<新>.py 后
alembic upgrade head
```

## 生产部署（P3-3）

### Docker 一键部署（推荐）

```bash
# 1. 克隆项目
git clone <your-repo-url> && cd astro-stock

# 2. （可选）编辑 docker-compose.yml 中的环境变量
#    必改：ASTRO_JWT_SECRET（随机长串）
#    可选：ASTRO_LLM_API_KEY（如需 AI 解读）

# 3. 一键启动
docker compose up -d

# 4. 确认服务
open http://localhost:8000/docs    # 后端 API 文档（Swagger）
open http://localhost:5173          # 前端
```

容器启动流程：Postgres（healthcheck）→ 后端（alembic 自动 migration → uvicorn）→ 前端（Vite dev）。

### 生产部署（Vercel + Railway）

| 服务 | 平台 | 配置要点 |
|------|------|----------|
| 前端 | Vercel | `frontend/` 为根目录，`build command: pnpm build`，`output: dist/`；`VITE_API_BASE=https://你的后端.railway.app/api` |
| 后端 | Railway | `backend/` 为根目录，`start command: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| 数据库 | Railway Postgres | `ASTRO_DB_URL: postgresql+psycopg://user:pass@host:5432/astrostock` |
| JWT 密钥 | Railway env | `ASTRO_JWT_SECRET: <随机 64 字符>` |
| LLM Key | Railway env | `ASTRO_LLM_API_KEY: ak-your-key-here` |

### 环境变量速查

```yaml
# docker-compose.yml environment 参考
ASTRO_JWT_SECRET: "prod-secret-change-me"     # 必改，建议 openssl rand -hex 32
ASTRO_LLM_API_KEY: "ak-your-key-here"         # 如无 LLM 可留空，interpret API 返回失败提示
ASTRO_DB_URL: "postgresql+psycopg://..."       # 容器内自动设为 Postgres
ASTRO_DEBUG: "false"                           # 生产关 debug
ASTRO_SCHEDULER_ENABLED: "true"                # 启用定时过运扫描
```

## 路线图

详见 [docs/design-doc.md](docs/design-doc.md)。

---

*"As above, so below. As in the markets, so in the stars."*
