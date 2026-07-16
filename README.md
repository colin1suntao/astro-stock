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

## 路线图

详见 [docs/design-doc.md](docs/design-doc.md)。

---

*"As above, so below. As in the markets, so in the stars."*
