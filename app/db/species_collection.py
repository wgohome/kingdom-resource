from functools import lru_cache
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database
from pymongo.errors import BulkWriteError
from requests import delete

from app.db.setup import get_collection
from app.models.species import (
    SpeciesBase,
    SpeciesDoc,
    SpeciesIn,
    SpeciesOut,
)


def find_all_species(db: Database) -> list[SpeciesOut]:
    SPECIES_COLL = get_collection(SpeciesDoc, db)
    return [
        SpeciesOut(**species_dict)
        for species_dict in SPECIES_COLL.find()
    ]


def enforce_no_existing_species(species_in_list: list[SpeciesIn], db: Database) -> None:
    SPECIES_COLL = get_collection(SpeciesDoc, db)
    taxids_present = [doc["tax"] for doc in SPECIES_COLL.find({}, {"_id": 0, "tax": 1})]
    taxids_new = [sp.tax for sp in species_in_list]
    overlaps = set(taxids_new) & set(taxids_present)
    if len(overlaps) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "description": "Some taxids already exist in the DB.",
                "taxids": list(overlaps),
                "recommendations": [
                    "To ignore existing taxids and insert only new taxids, add `skip_duplicates=True` to the query parameters.",
                    "To replace existing taxids, delete the current species document before inserting the new one."
                ]
            }
        )


def insert_many_species(species_in_list: list[SpeciesIn], db: Database) -> list[SpeciesOut]:
    SPECIES_COLL = get_collection(SpeciesDoc, db)
    to_insert = [
        SpeciesBase(**sp_in.dict(exclude_none=True)).dict(exclude_none=True)
        for sp_in in species_in_list
    ]
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
        # Return only newly inserted documents
        existing_ids = [doc['op']['_id'] for doc in e.details['writeErrors']]
        to_insert_ids = [doc['_id'] for doc in to_insert]
        new_ids = list(set(to_insert_ids) - set(existing_ids))
        pointer = SPECIES_COLL.find({
            "_id": {"$in": new_ids}
        })
        return [SpeciesOut(**doc) for doc in pointer]


def find_one_species_by_taxid(taxid: int, db: Database) -> SpeciesOut:
    SPECIES_COLL = get_collection(SpeciesDoc, db)
    species_dict = SPECIES_COLL.find_one({
        "tax": taxid
    })
    if species_dict is None:
        raise HTTPException(
            status_code=404,
            detail={
                "taxid": taxid,
                "description": f"species of taxid {taxid} not found",
                "recommendations": [
                    "Ensure taxid given in url is correct",
                    "Insert species into the DB via the species POST request endpoint"
                ],
            }
        )
    return species_dict


def find_species_id_from_taxid(taxid: int, db: Database) -> ObjectId:
    SPECIES_COLL = get_collection(SpeciesDoc, db)
    species_dict = SPECIES_COLL.find_one(
        {"tax": taxid},
        {"_id": 1}
    )
    if species_dict is None:
        raise HTTPException(
            status_code=404,
            detail={
                "taxid": taxid,
                "description": f"species of taxid {taxid} not found",
                "recommendations": [
                    "Ensure taxid given in url is correct",
                    "Insert species into the DB via the species POST request endpoint"
                ],
            }
        )
    return species_dict["_id"]


def delete_one_species(taxid: int, db: Database) -> SpeciesOut:
    SPECIES_COLL = get_collection(SpeciesDoc, db)
    deleted = SPECIES_COLL.find_one_and_delete(
        {"tax": taxid},
        {"_id": 0}
    )
    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail={
                "taxid": taxid,
                "description": f"species of taxid {taxid} not found",
                "recommendations": [
                    "Ensure taxid given in url is correct",
                    "Insert species into the DB via the species POST request endpoint"
                ],
            }
        )
    return SpeciesOut(**deleted)
