import math
from fastapi import HTTPException, status
from pymongo import ReturnDocument
from pymongo.database import Database
from pymongo.errors import BulkWriteError
from app.db.genes_collection import find_gene_id_from_label

from app.db.setup import get_collection
from app.db.species_collection import find_species_id_from_taxid
from app.models.gene import (
    GeneDoc,
)
from app.models.gene_annotation import (
    GeneAnnotationDoc,
    GeneAnnotationIn,
    GeneAnnotationOut,
    GeneAnnotationPage,
    GeneAnnotationProcessed,
    GeneAnnotationUpdate,
    GeneInput,
)
from app.models.shared import PyObjectId
from config import settings


def find_all_gas(
    page_num: int,
    db: Database,
    type: str | None = None,
    label: str | None = None,
) -> GeneAnnotationPage:
    GA_COLL = get_collection(GeneAnnotationDoc, db)
    # TODO: may not make sense to filter by labels, that would be a singular GET
    query_filters = {
        key: value
        for key, value in {"type": type, "label": label}.items()
        if value is not None
    }
    ga_docs = [
        GeneAnnotationOut(**gene_dict)
        for gene_dict in GA_COLL.find(query_filters)
        .skip((page_num - 1) * settings.PAGE_SIZE)
        .limit(settings.PAGE_SIZE)
    ]
    return GeneAnnotationPage(
        page_total=math.ceil(GA_COLL.estimated_document_count() / settings.PAGE_SIZE),
        curr_page=page_num,
        payload=ga_docs
    )


def find_one_ga(type: str, label: str, db: Database) -> GeneAnnotationOut:
    GA_COLL = get_collection(GeneAnnotationDoc, db)
    ga_dict = GA_COLL.find_one({"type": type, "label": label})
    if ga_dict is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "description": f"GeneAnnotation(type={type}, label={label} not found.",
                "recommendations": []
            }
        )
    return GeneAnnotationOut(**ga_dict)


def check_if_ga_exists(type: str, label: str, db: Database) -> bool:
    GA_COLL = get_collection(GeneAnnotationDoc, db)
    ga_dict = GA_COLL.find_one({"type": type, "label": label}, {"_id"})
    if ga_dict is None:
        return False
    return True


def insert_one_ga(ga_proc: GeneAnnotationProcessed, db: Database) -> GeneAnnotationOut:
    GA_COLL = get_collection(GeneAnnotationDoc, db)
    to_insert = ga_proc.dict(exclude_none=True)
    _ = GA_COLL.insert_one(to_insert)
    return GeneAnnotationOut(**to_insert)


# FIXME DEPRECATED
def insert_many_gas(ga_procs: list[GeneAnnotationProcessed], db: Database) -> list[GeneAnnotationOut]:
    GA_COLL = get_collection(GeneAnnotationDoc, db)
    to_insert = [ga_proc.dict_for_db() for ga_proc in ga_procs]
    try:
        result = GA_COLL.insert_many(
            to_insert,
            ordered=False
        )
        pointer = GA_COLL.find({
            "_id": {"$in": result.inserted_ids}
        })
        return [GeneAnnotationOut(**doc) for doc in pointer]
    except BulkWriteError as e:
        print(f"Only {e.details['nInserted']} / {len(to_insert)} genes are newly inserted into the genes collection")
        print(f"writeErrors: {e.details['writeErrors']}")
        # Return only newly inserted documents
        existing_ids = [doc['op']['_id'] for doc in e.details['writeErrors']]
        to_insert_ids = [doc['_id'] for doc in to_insert]
        new_ids = list(set(to_insert_ids) - set(existing_ids))
        pointer = GA_COLL.find({
            "_id": {"$in": new_ids}
        })
        return [GeneAnnotationOut(**doc) for doc in pointer]


def insert_or_replace_many_gas(ga_proc_list: list[GeneAnnotationProcessed], db: Database) -> list[GeneAnnotationOut]:
    GA_COLL = get_collection(GeneAnnotationDoc, db)
    final_docs = []
    for ga_proc in ga_proc_list:
        # gene_doc = GeneProcessed(
        #     species_id=species_id,
        #     **gene_in.dict_for_db()
        # )
        # # BUG: annotations array will be reset! If don't want to reset, use patch instead
        to_write = ga_proc.dict_for_db()
        _ = GA_COLL.replace_one(
            {"type": ga_proc.type, "label": ga_proc.label},
            to_write,
            upsert=True
        )
        final_docs.append(to_write)
        # BUG: _id is not updated in the dict
    return final_docs


def insert_one_new_ga_or_append_gene_ids(
    ga_proc: GeneAnnotationProcessed,
    db: Database
) -> GeneAnnotationOut:
    GA_COLL = get_collection(GeneAnnotationDoc, db)
    ga_dict = GA_COLL.find_one({"type": ga_proc.type, "label": ga_proc.label})
    if ga_dict is None:
        return insert_one_ga(ga_proc, db)
    updated = GA_COLL.find_one_and_update(
        {"type": ga_proc.type, "label": ga_proc.label},
        {
            "$addToSet": {"gene_ids": {"$each": ga_proc.gene_ids}},
            # "$setOnInsert": ga_proc.dict_for_db()
        },
        # upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return GeneAnnotationOut(**updated)


def delete_one_ga(ga_type: str, label: str, db: Database):
    GA_COLL = get_collection(GeneAnnotationDoc, db)
    deleted = GA_COLL.find_one_and_delete(
        {"type": ga_type, "label": label},
        {"_id": 0}
    )
    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail={
                "gene_annotation": {"type": ga_type, "label": label},
                "description": f"GeneAnnotation(type={ga_type}, label={label}) not found",
                "recommendations": [],
            }
        )
    return GeneAnnotationOut(**deleted)


def update_one_ga(ga_type: str, label: str, updates: GeneAnnotationUpdate, db: Database) -> GeneAnnotationOut:
    GA_COLL = get_collection(GeneAnnotationDoc, db)
    updated = GA_COLL.find_one_and_update(
        {"type": ga_type, "label": label},
        {"$set": updates.dict_for_update()},
        return_document=ReturnDocument.AFTER
    )
    return GeneAnnotationOut(**updated)


def enforce_no_existing_gas(gas_in: list[GeneAnnotationIn], db: Database) -> None:
    GA_COLL = get_collection(GeneAnnotationDoc, db)
    existing = []
    for ga_in in gas_in:
        ga_dict = GA_COLL.find_one(
            {"type": ga_in.type, "label": ga_in.label},
            {"_id": 0, "type": 1, "label": 1}
        )
        if ga_dict is not None:
            existing.append(ga_dict)
    if len(existing) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "existing_gene_annotations": existing,
                "description": "Some gene annotations already exists.",
                "recommendations": [
                    "Use the update endpoint to update this record",
                    "Or use the delete enpoint to delete this record before posting a new one"
                ]
            }
        )


def enforce_no_existing_ga(ga_in: GeneAnnotationIn, db: Database) -> None:
    GA_COLL = get_collection(GeneAnnotationDoc, db)
    ga_dict = GA_COLL.find_one({"type": ga_in.type, "label": ga_in.label}, {"label": 1})
    if ga_dict is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "description": f"GeneAnnotation(type={ga_in.type}, label={ga_in.label} already exists.",
                "recommendations": [
                    "Use the update endpoint to update this record",
                    "Or use the delete enpoint to delete this record before posting a new one"
                ]
            }
        )


def gene_labels_to_ids(genes: list[GeneInput], db: Database) -> list[PyObjectId]:
    GENE_COLL = get_collection(GeneDoc, db)
    # TODO if gene not found, to return an array of error instead of raising only one at a time
    query = []
    for gene in genes:
        # These find methods will raise 404 if species or gene not found
        spe_id = find_species_id_from_taxid(gene.taxid, db)
        _ = find_gene_id_from_label(spe_id, gene.gene_label, db)
        query.append({
            "spe_id": spe_id,
            "label": gene.gene_label
        })
    if query == []:  # avoid pymongo.errors.OperationFailure
        return query
    cursor = GENE_COLL.find(
        {"$or": query},
        {"_id": 1}
    )
    return [doc["_id"] for doc in cursor]


def convert_ga_in_to_ga_proc(ga_in: GeneAnnotationIn, db: Database) -> GeneAnnotationProcessed:
    gene_ids = gene_labels_to_ids(ga_in.genes, db)
    return GeneAnnotationProcessed(
        type=ga_in.type,
        label=ga_in.label,
        details=ga_in.details,
        gene_ids=gene_ids
    )
