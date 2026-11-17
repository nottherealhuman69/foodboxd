"""Entry point kept so `uvicorn main:app` (run from backend/) keeps working.

The application itself lives in the app/ package; see app/main.py.
"""
from app.main import app  # noqa: F401
