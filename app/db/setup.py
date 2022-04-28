from pymongo import MongoClient

from config import settings

client = MongoClient(settings.DATABASE_URL)
db = client[settings.DATABASE_NAME]


def get_collection(cls):
    return db[cls.Mongo.collection_name]
