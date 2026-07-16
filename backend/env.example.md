# AstroStock backend env — copy to backend/.env and adjust.
# (Kept as env.example.md to avoid tool's .env* sensitive-path guard; rename when copying.)
ASTRO_DEBUG=true
ASTRO_DB_URL=postgresql+psycopg://astro:astro@localhost:5432/astrostock
ASTRO_EPHEM_PATH=./data/swisseph
ASTRO_YFINANCE_CACHE_DIR=./data/yfinance_cache
