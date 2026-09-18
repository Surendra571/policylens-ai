import os

# Ensure tests run with SQLite fallback unless explicit PostgreSQL host is configured
os.environ.setdefault("USE_SQLITE", "True")

