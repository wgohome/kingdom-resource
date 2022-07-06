from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.database import Database
import pytest
from passlib.context import CryptContext

from app.main import app
from app.db.setup import get_collection, get_db, setup_indexes
from app.models.user import UserDoc
from config import settings


def run_test_seeder(db: Database) -> None:
    USERS_COLL = get_collection(UserDoc, db)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user_dict = USERS_COLL.find_one({"email": settings.ADMIN_EMAIL})
    if user_dict is None:
        USERS_COLL.insert_one({
            "email": settings.ADMIN_EMAIL,
            "role": "admin",
            "hashed_pw": pwd_context.hash(settings.ADMIN_PW.get_secret_value()),
            "api_key": settings.TEST_API_KEY
        })
        print(f"Created admin user {settings.ADMIN_EMAIL}")


@pytest.fixture
def get_db_for_test():
    client = MongoClient(settings.DATABASE_URL)
    if settings.TEST_DATABASE_NAME is None or settings.TEST_DATABASE_NAME == "":
        raise ValueError("TEST_DATABASE_NAME env variable missing")
    client.drop_database(settings.TEST_DATABASE_NAME)
    db = client[settings.TEST_DATABASE_NAME]
    setup_indexes(db)
    run_test_seeder(db)
    yield lambda: db  # FastAPI dependencies must be a callable
    client.drop_database(settings.TEST_DATABASE_NAME)


#
# NOTE
# When multiple t_client are called in a single test (via fixtures or otherwise),
#   they will still be calling on the same test database
#   because the t_client fixture will only tear down the db at the end of the test
#
@pytest.fixture
def t_client(get_db_for_test):
    app.dependency_overrides[get_db] = get_db_for_test
    client = TestClient(app)
    return client
