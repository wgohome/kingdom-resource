from functools import lru_cache
from pymongo import MongoClient

from config import settings


@lru_cache
def get_db():
    client = MongoClient(settings.DATABASE_URL)
    if settings.DATABASE_NAME is None or settings.DATABASE_NAME == "":
        raise ValueError("DATABASE_NAME env variable missing")
    db = client[settings.DATABASE_NAME]
    return db
    # Returns db instead of yield as we are using lru_cache
    # With yield, a generator will be returned and
    # subsequent calls to get_db as a dependancy will yield nothing
