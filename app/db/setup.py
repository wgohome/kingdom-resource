from enum import unique
from functools import lru_cache
from pydantic.main import ModelMetaclass
from pymongo import ASCENDING, MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

from app.models.genes import GeneDoc
from app.models.sample_annotation import SampleAnnotationDoc
from app.models.species import SpeciesDoc
from config import settings


def setup_indexes(db):
    #
    # To search species by their taxid
    # and enforce unique taxids
    db[SpeciesDoc.Mongo.collection_name].create_index(
        [("tax", ASCENDING)],
        unique=True,
        name="unique_taxids"
    )
    #
    # To search gene by their species and/or gene label
    # and enforce unique gene labels within each species scope
    db[GeneDoc.Mongo.collection_name].create_index(
        [("spe_id", ASCENDING), ("label", ASCENDING)],
        unique=True,
        name="unique_species_gene_labels"
    )
    #
    # To search sample annotations by type + label, gene
    db[SampleAnnotationDoc.Mongo.collection_name].create_index(
        [
            ("spe_id", ASCENDING),
            ("g_id", ASCENDING),
            ("type", ASCENDING),
            ("lbl", ASCENDING),
        ],
        unique=True,
        name="unique_sample_annotation_doc"
    )
    # TODO
    # test if the unique constraint working
    # see if need more index for searching by species and gene


@lru_cache
def get_db():
    client = MongoClient(settings.DATABASE_URL)
    if settings.DATABASE_NAME is None or settings.DATABASE_NAME == "":
        raise ValueError("DATABASE_NAME env variable missing")
    db = client[settings.DATABASE_NAME]
    setup_indexes(db)
    return db
    # Returns db instead of yield as we are using lru_cache
    # With yield, a generator will be returned and
    # subsequent calls to get_db as a dependancy will yield nothing


@lru_cache
def get_collection(model: ModelMetaclass, db: Database) -> Collection:
    assert hasattr(model, "Mongo"), f"{model.__name__} should inherit from DocumentBaseModel"
    return db[model.Mongo.collection_name]  # type: ignore
