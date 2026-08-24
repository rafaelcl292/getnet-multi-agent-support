import os

os.environ["DEMO_MODE"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def client():
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client

