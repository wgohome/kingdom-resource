from functools import lru_cache
from fastapi import HTTPException, status
from pymongo.database import Database
from pymongo.errors import BulkWriteError
from pydantic.main import ModelMetaclass

from app.models.species import SpeciesDoc, SpeciesIn, SpeciesOut


@lru_cache
def __get_collection(model: ModelMetaclass, db):
    assert hasattr(model, "Mongo"), "ModelMetaclass should inherit from DocumentBaseModel"
    return db[model.Mongo.collection_name]  # type: ignore


def find_all_species(db: Database):
    SPECIES_COLL = __get_collection(SpeciesDoc, db)
    return [
        SpeciesOut(**species_dict)
        for species_dict in SPECIES_COLL.find()
    ]


def enforce_no_existing_species(species_in_list: list[SpeciesIn], db: Database):
    SPECIES_COLL = __get_collection(SpeciesDoc, db)
    taxids_present = [doc["tax"] for doc in SPECIES_COLL.find({}, {"_id": 0, "tax": 1})]
    taxids_new = [sp.tax for sp in species_in_list]
    overlaps = set(taxids_new) & set(taxids_present)
    if len(overlaps) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "description": "Some taxids already in the DB.",
                "taxids": list(overlaps),
                "recommendations": [
                    "To ignore existing taxids and insert only new taxids, add `skip_duplicates=True` to the query parameters.",
                    "To replace existing taxids, delete the current species document before inserting the new one."
                ]
            }
        )


def insert_many_species(species_in_list: list[SpeciesIn], db: Database):
    SPECIES_COLL = __get_collection(SpeciesDoc, db)
    to_insert = [sp_in.dict(exclude_none=True) for sp_in in species_in_list]
    try:
        result = SPECIES_COLL.insert_many(
            to_insert,
            ordered=False
        )
        pointer = SPECIES_COLL.find({
            "_id": {"$in": result.inserted_ids}
        })
        return [SpeciesOut(**doc) for doc in pointer]
    except BulkWriteError as e:
        print(f"Only {e.details['nInserted']} / {len(to_insert)} species is newly inserted into the species collection")
        print(f"writeErrors: {e.details['writeErrors']}")
    return to_insert


def find_one_species_by_taxid(taxid: int, db: Database):
    SPECIES_COLL = __get_collection(SpeciesDoc, db)
    species_dict = SPECIES_COLL.find_one({
        "tax": taxid
    })
    if species_dict is None:
        raise HTTPException(
            status_code=404,
            detail=f"species of taxid {taxid} not found"
        )
    return species_dict
