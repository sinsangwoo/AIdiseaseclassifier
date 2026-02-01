"""
Root-level Flask application wrapper for backward compatibility.

This file serves as an entry point for deployment platforms (e.g., Render)
that expect app.py to be in the root directory.

For new deployments, use backend.app:app directly via:
  gunicorn backend.app:app

This wrapper maintains compatibility with legacy Start Commands:
  gunicorn app:app
"""

from backend.app import app

if __name__ == "__main__":
    app.run()
