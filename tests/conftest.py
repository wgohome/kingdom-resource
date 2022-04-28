from pymongo import MongoClient
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.setup import get_db
from config import settings


@pytest.fixture
def get_db_for_test():
    client = MongoClient(settings.DATABASE_URL)
    if settings.TEST_DATABASE_NAME is None or settings.TEST_DATABASE_NAME == "":
        raise ValueError("TEST_DATABASE_NAME env variable missing")
    db = client[settings.TEST_DATABASE_NAME]
    yield lambda: db  # FastAPI dependencies must be a callable
    client.drop_database(settings.TEST_DATABASE_NAME)


@pytest.fixture
def t_client(get_db_for_test):
    app.dependency_overrides[get_db] = get_db_for_test
    client = TestClient(app)
    return client
