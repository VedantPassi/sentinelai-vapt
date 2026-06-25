import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}+{uuid.uuid4().hex[:8]}@test.dev"


@pytest.fixture(autouse=True)
async def dispose_engine():
    yield
    from core.db import engine
    await engine.dispose()
