from fastapi import HTTPException, status
# from pydantic import ValidationError
from pymongo import ReplaceOne, ReturnDocument
from pymongo.database import Database
from pymongo.errors import BulkWriteError

from app.db.setup import get_collection
from app.models.shared import PyObjectId
from app.models.species import (
    SpeciesBase,
    SpeciesDoc,
    SpeciesIn,
    SpeciesOut,
    SpeciesPage,
    SpeciesUpdate,
)
from config import settings


def find_all_species(page_num: int, db: Database) -> SpeciesPage:
    SPECIES_COLL = get_collection(SpeciesDoc, db)
    species_docs = [
        SpeciesOut(**species_dict)
        for species_dict in SPECIES_COLL.find()
        .skip((page_num - 1) * settings.PAGE_SIZE)
        .limit(settings.PAGE_SIZE)
    ]
    return SpeciesPage(
        page_total=SPECIES_COLL.estimated_document_count(),
        curr_page=page_num,
        payload=species_docs
    )
    # try:
    #     return SpeciesPage(
    #         page_total=SPECIES_COLL.estimated_document_count(),
    #         curr_page=page_num,
    #         payload=species_docs
    #     )
    # except ValidationError as e:
    #     # If error is regarding `curr_page` > `page_total`, tell client
    #     if e.errors()[0]["loc"][0] == "curr_page" and e.errors()[0]["type"] == "value_error":
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail=f"`page_num={page_num}` is out of range"
    #         )
    #     # Otherwise, raise the error to logs, but not expose it to client
    #     raise e


def insert_one_species(species_in: SpeciesIn, db: Database) -> SpeciesOut:
    SPECIES_COLL = get_collection(SpeciesDoc, db)
    species_doc = SpeciesBase(**species_in.dict_for_db())
    to_insert = species_doc.dict_for_db()
    _ = SPECIES_COLL.insert_one(to_insert)
    return SpeciesOut(**to_insert)


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


def insert_or_replace_many_species(species_in_list: list[SpeciesIn], db: Database) -> list[SpeciesOut]:
    SPECIES_COLL = get_collection(SpeciesDoc, db)
    final_docs = []
    for sp_in in species_in_list:
        sp_doc = SpeciesDoc(**sp_in.dict_for_db())
        to_write = sp_doc.dict_for_db()
        result = SPECIES_COLL.replace_one(
            {"tax": sp_doc.tax},
            to_write,
            upsert=True
        )
        final_docs.append(to_write)
        # BUG: _id is not updated in the dict
    return final_docs


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


def update_one_species(species_id: PyObjectId, updates: SpeciesUpdate, db: Database) -> SpeciesOut:
    SPECIES_COLL = get_collection(SpeciesDoc, db)
    updated = SPECIES_COLL.find_one_and_update(
        {"_id": species_id},
        {"$set": updates.dict(exclude_unset=True)},
        return_document=ReturnDocument.AFTER
    )
    return SpeciesOut(**updated)


def enforce_no_existing_species_in_list(species_in_list: list[SpeciesIn], db: Database) -> None:
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
                    "To replace existing taxids, delete the current species document before inserting the new one.",
                    "Alternatively, to replace species docs in bulk, use the bulk PUT request at the same url path"
                ]
            }
        )


def enforce_taxid_not_exist(taxid: int, db: Database) -> None:
    SPECIES_COLL = get_collection(SpeciesDoc, db)
    species = SPECIES_COLL.find_one({"tax": taxid}, {"_id": 1})
    if species is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "taxid": taxid,
                "description": f"species of taxid {taxid} already exists",
                "recommendations": [
                    "You may update the existing species record via the PATCH endpoint",
                    "You may delete the existing species record before POST-ing a new one with the same taxid",
                ],
            }
        )
    return None


def find_species_id_from_taxid(taxid: int, db: Database) -> PyObjectId:
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
    return PyObjectId(species_dict["_id"])


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
    # TODO: Load into model for typecast checks
    return species_dict
