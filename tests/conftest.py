import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def t_client():
    client = TestClient(app)
    yield client
