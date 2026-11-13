"""Vercel Python Function entry point: serves the FastAPI app for /api/* and /health."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.main import app  # noqa: E402,F401
