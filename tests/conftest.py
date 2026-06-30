import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use in-memory SQLite for tests before app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEMO_API_KEY", "test-api-key")
os.environ.setdefault("SEMANTIC_CACHE_ENABLED", "false")
os.environ.setdefault("OLLAMA_BASE_URL", "")
os.environ.setdefault("MOCK_FAILURE_RATE", "0.0")

from app.config import get_settings

get_settings.cache_clear()

from app.storage.db import init_db
from app.storage.models import Base

init_db()
