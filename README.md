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

## 路线图

详见 [docs/design-doc.md](docs/design-doc.md)。

---

*"As above, so below. As in the markets, so in the stars."*
