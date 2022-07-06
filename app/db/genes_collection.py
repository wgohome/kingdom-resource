import math
from fastapi import HTTPException, status
from pymongo import ReturnDocument
from pymongo.database import Database
from pymongo.errors import BulkWriteError

from app.db.setup import get_collection
from app.db.species_collection import find_species_id_from_taxid
from app.models.gene import (
    GeneDoc,
    GeneIn,
    GeneOut,
    GenePage,
    GeneProcessed,
)
from app.models.shared import PyObjectId
from config import settings


def find_all_genes_by_species(
    species_id: PyObjectId, page_num: int, db: Database
) -> GenePage:
    GENES_COLL = get_collection(GeneDoc, db)
    gene_docs = [
        GeneOut(**gene_dict)
        for gene_dict in GENES_COLL.find({"spe_id": species_id})
        .skip((page_num - 1) * settings.PAGE_SIZE)
        .limit(settings.PAGE_SIZE)
    ]
    return GenePage(
        page_total=math.ceil(GENES_COLL.estimated_document_count() / settings.PAGE_SIZE),
        curr_page=page_num,
        payload=gene_docs
    )


def insert_one_gene(gene_processed: GeneProcessed, db: Database):
    GENES_COLL = get_collection(GeneDoc, db)
    to_insert = gene_processed.dict_for_db()
    _ = GENES_COLL.insert_one(to_insert)
    return GeneOut(**to_insert)


def insert_many_genes(
    genes_processed: list[GeneProcessed],
    db: Database
) -> list[GeneOut]:
    #
    # Species Mongo ID should already be updated in genes_in list
    # before passing to this function.
    # This is validated by the GeneProcessed Pydantic model.
    #
    GENES_COLL = get_collection(GeneDoc, db)
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


def insert_or_replace_many_genes(
    species_id: PyObjectId,
    genes_in_list: list[GeneIn],
    db: Database
) -> list[GeneOut]:
    GENES_COLL = get_collection(GeneDoc, db)
    final_docs = []
    for gene_in in genes_in_list:
        gene_doc = GeneProcessed(
            species_id=species_id,
            **gene_in.dict_for_db()
        )
        # BUG: annotations array will be reset! If don't want to reset, use patch instead
        to_write = gene_doc.dict_for_db()
        _ = GENES_COLL.replace_one(
            {"spe_id": species_id, "label": gene_doc.label},
            to_write,
            upsert=True
        )
        final_docs.append(to_write)
        # BUG: _id is not updated in the dict
    return final_docs


def delete_one_gene(taxid: int, gene_label: str, db: Database) -> GeneOut:
    GENES_COLL = get_collection(GeneDoc, db)
    species_id = find_species_id_from_taxid(taxid, db)
    deleted = GENES_COLL.find_one_and_delete(
        {"spe_id": species_id, "label": gene_label},
        {"_id": 0}
    )
    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail={
                "gene_label": gene_label,
                "description": f"gene {gene_label} for species taxid {taxid} not found",
                "recommendations": [],
            }
        )
    return GeneOut(**deleted)


def update_one_gene(species_id: PyObjectId, gene_label: str, updates: GeneIn, db: Database) -> GeneOut:
    GENES_COLL = get_collection(GeneDoc, db)
    updated = GENES_COLL.find_one_and_update(
        {"spe_id": species_id, "label": gene_label},
        {"$set": updates.dict(exclude_unset=True)},
        return_document=ReturnDocument.AFTER
    )
    return GeneOut(**updated)


def add_annotations_to_gene(gene_id: PyObjectId, ga_ids: list[PyObjectId], db: Database) -> GeneOut:
    GENES_COLL = get_collection(GeneDoc, db)
    updated = GENES_COLL.find_one_and_update(
        {"_id": gene_id},
        {"$push": {"anots": {"$each": ga_ids}}}
    )
    return updated


def enforce_no_existing_genes(species_id: PyObjectId, genes_in: list[GeneIn], db: Database) -> None:
    # Uniqueness is enforced within the scope of the species only
    GENES_COLL = get_collection(GeneDoc, db)
    labels_present = [
        doc["label"]
        for doc in GENES_COLL.find(
            {"spe_id": species_id},
            {"_id": 0, "label": 1}
        )
    ]
    labels_new = [gene.label for gene in genes_in]
    overlaps = set(labels_new) & set(labels_present)
    if len(overlaps) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "description": "Some gene labels (identifiers) already exist in the DB. Under each species, gene labels must be unique",
                "gene_labels": list(overlaps),
                "recommendations": [
                    "To ignore existing gene labels and insert only new gene labels, add `skip_duplicates=True` to the query parameters.",
                    "To replace existing gene labels, delete the current gene document before inserting the new one.",
                    "Check that you are inserting genes into the correct species",
                    "If gene has isoforms, consider suffixing the label"
                ]
            }
        )


def find_gene_id_from_label(species_id: PyObjectId, gene_label: str, db: Database) -> PyObjectId:
    GENE_COLL = get_collection(GeneDoc, db)
    gene_dict = GENE_COLL.find_one(
        {"spe_id": species_id, "label": gene_label},
        {"_id": 1}
    )
    if gene_dict is None:
        raise HTTPException(
            status_code=404,
            detail={
                "gene_label": gene_label,
                "description": f"gene of identifier label {gene_label} not found",
                "recommendations": [
                    "Ensure gene label is the main gene identifier label and not their alias",
                    "If gene has not been inserted into database, insert genes into the DB via the post_many_genes_by_species POST request endpoint",
                ],
            }
        )
    return PyObjectId(gene_dict["_id"])


def find_one_gene_by_label(species_id: PyObjectId, gene_label: str, db: Database) -> GeneOut:
    GENE_COLL = get_collection(GeneDoc, db)
    gene_dict = GENE_COLL.find_one(
        {"spe_id": species_id, "label": gene_label}
    )
    if gene_dict is None:
        raise HTTPException(
            status_code=404,
            detail={
                "gene_label": gene_label,
                "description": f"gene of identifier label {gene_label} not found",
                "recommendations": [
                    "Ensure gene label is the main gene identifier label and not their alias",
                    "If gene has not been inserted into database, insert genes into the DB via the post_many_genes_by_species POST request endpoint",
                ],
            }
        )
    return GeneOut(**gene_dict)
