# Vercel serverless entry point.
# Vercel's @vercel/python runtime detects the ASGI `app` object exported here
# and wraps it to handle HTTP requests. All routing stays inside FastAPI.
from app.main import app
