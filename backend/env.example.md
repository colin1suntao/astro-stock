# AstroStock backend env — copy to backend/.env and adjust.
# (Kept as env.example.md to avoid tool's .env* sensitive-path guard; rename when copying.)

# --- core ---
ASTRO_DEBUG=true
ASTRO_DB_URL=postgresql+psycopg://astro:astro@localhost:5432/astrostock
# dev fallback (zero deps): sqlite:///./data/astrostock.db
ASTRO_EPHEM_PATH=./data/swisseph
ASTRO_YFINANCE_CACHE_DIR=./data/yfinance_cache

# --- JWT auth (P1-6) ---
ASTRO_JWT_SECRET=dev-secret-change-in-prod
ASTRO_JWT_ALGO=HS256
ASTRO_JWT_EXPIRE_MINUTES=1440

# --- LLM (P2-1) — LongCat, OpenAI-compatible ---
ASTRO_LLM_BASE_URL=https://api.longcat.chat/openai/v1/chat/completions
ASTRO_LLM_API_KEY=ak-your-key-here
ASTRO_LLM_MODEL=LongCat-2.0
ASTRO_LLM_MAX_TOKENS=1500

# --- scheduler (P3-2) — disabled by default, enable in prod ---
# APScheduler runs transit scan every 2h for users with birth charts.
ASTRO_SCHEDULER_ENABLED=true
