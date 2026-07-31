# Vercel serverless entry point.
# Vercel's @vercel/python runtime detects the ASGI `app` object exported here
# and wraps it to handle HTTP requests. All routing stays inside FastAPI.
import os
import sys

# Vercel mounts this function from backend/api/, so make sure the backend root
# (one level up) is on sys.path for `from app...` imports to resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The FastAPI instance is defined in app/main.py (the "main" submodule of the "app" package).
import importlib.util

# Load the FastAPI app directly from app/main.py by filesystem path, so we
# don't depend on a particular import-name spelling.
_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_main_path = os.path.join(_backend_root, "app", "main.py")
_spec = importlib.util.spec_from_file_location("_astrostock_main", _main_path)
_app_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_app_main)
app = _app_main.app
