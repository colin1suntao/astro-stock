FROM python:3.12-slim
WORKDIR /app

# Install build deps for psycopg/scipy, then clean
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Install deps first (cache layer)
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy app + migrations
COPY . .

# Run alembic migration on container start (idempotent — safe if already head)
# Expose 8000 + run uvicorn
ENV ASTRO_DB_URL=postgresql+psycopg://astro:astro@db:5432/astrostock
EXPOSE 8000

# migrate then serve — so fresh DB auto-creates tables
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
