FROM python:3.12-slim
WORKDIR /app

# Install build deps for psycopg/scipy, then clean
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Install deps first (cache layer)
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy app + migrations + entrypoint
COPY . .
RUN chmod +x /app/entrypoint.sh

# Expose 8000 + run via entrypoint (wait db → migrate → serve)
ENV ASTRO_DB_URL=postgresql+psycopg://astro:astro@db:5432/astrostock
EXPOSE 8000
CMD ["/app/entrypoint.sh"]
