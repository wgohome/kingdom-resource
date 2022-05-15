from functools import lru_cache
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database
from pymongo.errors import BulkWriteError
from pydantic.main import ModelMetaclass

from app.models.genes import GeneDoc, GeneIn, GeneOut, GeneProcessed


@lru_cache
def __get_collection(model: ModelMetaclass, db: Database):
    assert hasattr(model, "Mongo"),  f"{model.__name__} should inherit from DocumentBaseModel"
    return db[model.Mongo.collection_name]


def find_all_genes_by_species(species_id: ObjectId, db: Database) -> list[GeneOut]:
    GENES_COLL = __get_collection(GeneDoc, db)
    return [
        GeneOut(**gene_dict)
        for gene_dict in GENES_COLL.find({"spe_id": species_id})
    ]


def enforce_no_existing_genes(genes_in: list[GeneIn], db: Database) -> None:
    GENES_COLL = __get_collection(GeneDoc, db)
    labels_present = [doc["label"] for doc in GENES_COLL.find({}, {"_id": 0, "label": 1})]
    labels_new = [gene.label for gene in genes_in]
    overlaps = set(labels_new) & set(labels_present)
    if len(overlaps) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "description": "Some gene labels (identifiers) already exist in the DB. Gene labels must be unique",
                "gene_labels": list(overlaps),
                "recommendations": [
                    "To ignore existing gene labels and insert only new gene labels, add `skip_duplicates=True` to the query parameters.",
                    "To replace existing gene labels, delete the current gene document before inserting the new one.",
                    "If gene label indeed clash with other species, consdier prefixing the label with species identifier"
                ]
            }
        )


def insert_many_genes(
    genes_processed: list[GeneProcessed],
    db: Database
) -> list[GeneOut]:
    #
    # Species Mongo ID should already be updated in genes_in list
    # before passing to this function.
    # This is validated by the GeneProcessed Pydantic model.
    #
    GENES_COLL = __get_collection(GeneDoc, db)
    to_insert = [gene.dict(exclude_none=True) for gene in genes_processed]
    try:
        result = GENES_COLL.insert_many(
            to_insert,
            ordered=False
        )
        pointer = GENES_COLL.find({
            "_id": {"$in": result.inserted_ids}
        })
        return [GeneOut(**doc) for doc in pointer]
    except BulkWriteError as e:
        print(f"Only {e.details['nInserted']} / {len(to_insert)} genes are newly inserted into the genes collection")
        print(f"writeErrors: {e.details['writeErrors']}")
        # Return only newly inserted documents
        existing_ids = [doc['op']['_id'] for doc in e.details['writeErrors']]
        to_insert_ids = [doc['_id'] for doc in to_insert]
        new_ids = list(set(to_insert_ids) - set(existing_ids))
        pointer = GENES_COLL.find({
            "_id": {"$in": new_ids}
        })
        return [GeneOut(**doc) for doc in pointer]
