from functools import lru_cache
import uuid
from pydantic.main import ModelMetaclass
from pymongo import ASCENDING, MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from passlib.context import CryptContext

from app.models.gene import GeneDoc
from app.models.gene_annotation import GeneAnnotationDoc
from app.models.sample_annotation import SampleAnnotationDoc
from app.models.species import SpeciesDoc
from app.models.user import UserDoc
from config import settings


def setup_indexes(db):
    #
    # To search species by their taxid
    # and enforce unique taxids
    #
    get_collection(SpeciesDoc, db).create_index(
        [("tax", ASCENDING)],
        unique=True,
        name="unique_taxids"
    )
    #
    # To search gene by their species and/or gene label
    # and enforce unique gene labels within each species scope
    #
    get_collection(GeneDoc, db).create_index(
        [("spe_id", ASCENDING), ("label", ASCENDING)],
        unique=True,
        name="unique_species_gene_labels"
    )
    #
    # To search gene annotations by type and label
    # and enforce uniqueness
    #
    get_collection(GeneAnnotationDoc, db).create_index(
        [("type", ASCENDING), ("label", ASCENDING)],
        unique=True,
        name="unique_gene_annotations_type_and_label"
    )
    #
    # To search sample annotations by type + label, gene
    #
    get_collection(SampleAnnotationDoc, db).create_index(
        [
            ("spe_id", ASCENDING),
            ("g_id", ASCENDING),
            ("type", ASCENDING),
            ("lbl", ASCENDING),
        ],
        unique=True,
        name="unique_sample_annotation_doc"
    )
    #
    # To search for users by email
    #
    get_collection(UserDoc, db).create_index(
        [("email", ASCENDING)],
        unique=True,
        name="unique_email_for_users"
    )
    #
    # To enforce unique api_keys
    #
    get_collection(UserDoc, db).create_index(
        "api_key",
        unique=True,
        name="unique_api_key_for_users"
    )


def run_seeder(db: Database) -> None:
    USERS_COLL = get_collection(UserDoc, db)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user_dict = USERS_COLL.find_one({"email": settings.ADMIN_EMAIL})
    if user_dict is None:
        USERS_COLL.insert_one({
            "email": settings.ADMIN_EMAIL,
            "role": "admin",
            "hashed_pw": pwd_context.hash(settings.ADMIN_PW.get_secret_value()),
            "api_key": uuid.uuid4().hex
        })
        print(f"Created admin user {settings.ADMIN_EMAIL}")


@lru_cache
def get_db():
    client = MongoClient(settings.DATABASE_URL)
    if settings.DATABASE_NAME is None or settings.DATABASE_NAME == "":
        raise ValueError("DATABASE_NAME env variable missing")
    db = client[settings.DATABASE_NAME]
    setup_indexes(db)
    if settings.FASTAPI_ENV in ["production", "development", "staging"]:
        run_seeder(db)
    return db
    # Returns db instead of yield as we are using lru_cache
    # With yield, a generator will be returned and
    # subsequent calls to get_db as a dependancy will yield nothing


@lru_cache
def get_collection(model: ModelMetaclass, db: Database) -> Collection:
    assert hasattr(model, "Mongo"), f"{model.__name__} should inherit from DocumentBaseModel"
    return db[model.Mongo.collection_name]  # type: ignore
