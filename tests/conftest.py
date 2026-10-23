from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

# Ensure test isolation: point DB and outputs to temp dirs BEFORE importing backend
_TMP = tempfile.mkdtemp(prefix="fanjha-test-")
os.environ["FANJHA_DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/test.db"
os.environ["FANJHA_ARTIFACTS_DIR"] = f"{_TMP}/outputs"
os.environ["FANJHA_LOGS_DIR"] = f"{_TMP}/logs"
os.environ["FANJHA_DATA_DIR"] = f"{_TMP}/data"
os.environ["FANJHA_MAX_TRAIN_STEPS"] = "2"
os.environ["FANJHA_RATE_LIMIT_BUILDS_PER_MINUTE"] = "100"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport, AsyncClient
    from backend.main import app
    from backend.database import init_db

    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def csrf_headers():
    from backend.config import settings

    return {"X-CSRF-Token": settings.csrf_secret}
