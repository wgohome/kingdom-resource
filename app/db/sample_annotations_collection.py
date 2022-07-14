import math
from os import pidfd_open
from bson import ObjectId
from collections import defaultdict
from fastapi import HTTPException, status
from pymongo.database import Database
from pymongo.errors import BulkWriteError

from config import settings
from app.db.setup import get_collection
from app.models.sample_annotation import (
    Sample,
    SampleAnnotationDoc,
    SampleAnnotationInput,
    SampleAnnotationOut,
    SampleAnnotationPage,
    SampleAnnotationUnit,
)


def find_sample_annotations_by_gene(
    species_id: ObjectId,
    gene_id: ObjectId,
    page_num: int,
    db: Database
) -> SampleAnnotationPage:
    SA_COLL = get_collection(SampleAnnotationDoc, db)
    sa_docs = [
        SampleAnnotationOut(**sa_dict)
        for sa_dict in SA_COLL.find({"spe_id": species_id, "g_id": gene_id})
        .skip((page_num - 1) * settings.PAGE_SIZE)
        .limit(settings.PAGE_SIZE)
    ]
    return SampleAnnotationPage(
        page_total=math.ceil(SA_COLL.estimated_document_count() / settings.PAGE_SIZE),
        curr_page=page_num,
        payload=sa_docs
    )


def find_sample_annotations_by_label(
    annotation_type: str,
    annotation_label: str,
    page_num: int,
    db: Database
) -> SampleAnnotationPage:
    SA_COLL = get_collection(SampleAnnotationDoc, db)
    sa_docs = [
        SampleAnnotationOut(**sa_dict)
        for sa_dict in SA_COLL.find({"type": annotation_type, "label": annotation_label})
        .skip((page_num - 1) * settings.PAGE_SIZE)
        .limit(settings.PAGE_SIZE)
    ]
    return SampleAnnotationPage(
        page_total=math.ceil(SA_COLL.estimated_document_count() / settings.PAGE_SIZE),
        curr_page=page_num,
        payload=sa_docs
    )


def __group_samples_by_annotation_labels(
    samples: list[SampleAnnotationUnit]
) -> dict[str, list[Sample]]:
    groups = defaultdict(list)
    for row in samples:
        groups[row.annotation_label].append(Sample(
            sample_label=row.sample_label,
            tpm_value=round(row.tpm, settings.N_DECIMALS)
        ))
    return groups


def reshape_sa_input_to_sa_docs(
    sa_input: SampleAnnotationInput,
    species_id: ObjectId,
    gene_id: ObjectId
) -> list[SampleAnnotationDoc]:
    groups = __group_samples_by_annotation_labels(sa_input.samples)
    return [
        SampleAnnotationDoc(
            species_id=species_id,
            gene_id=gene_id,
            type=sa_input.annotation_type,
            label=annotation_label,
            samples=samples
        )  # type: ignore
        for annotation_label, samples in groups.items()
    ]


def enforce_no_existing_samples_for_gene(
    sa_input: SampleAnnotationInput,
    species_id: ObjectId,
    gene_id: ObjectId,
    db: Database
) -> None:
    # When this function is called,
    #   it is assumed to be scoped to one gene, of one species only
    SA_COLL = get_collection(SampleAnnotationDoc, db)
    annotations = SA_COLL.aggregate([
        {"$match": {"spe_id": species_id, "g_id": gene_id}},
        {"$unwind": "$samples"},
        {"$project": {"_id": 0, "label": "$samples.label"}},
    ])
    existing_samples = {res["label"] for res in annotations}
    incoming_samples = {row.sample_label for row in sa_input.samples}
    if existing_samples & incoming_samples != set():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "description": "Some sample labels (accessions) already exist in the DB. Sample labels must be unique",
                "sample_labels": list(existing_samples & incoming_samples),
                "recommendations": [
                    "To ignore existing sample labels and append only new sample labels, add `skip_duplicate_samples=True` to the query parameters.",
                    "To replace existing sample labels, use the update endpoint for SampleAnnotationDoc instead.",
                    "Sample accession labels should be unique",
                ]
            }
        )


def insert_or_update_one_sa_doc(
    sa_doc: SampleAnnotationDoc,
    db: Database
) -> SampleAnnotationOut:
    # If sample annotation type + label does not exist yet, insert one new doc
    # If it exists,
    #   Check which samples within the new SA input doc are new
    #   Update the sa doc with only the new samples, and not replace the existing samples
    SA_COLL = get_collection(SampleAnnotationDoc, db)
    curr_doc_dict = SA_COLL.find_one({
        "spe_id": sa_doc.spe_id,
        "g_id": sa_doc.g_id,
        "type": sa_doc.type,
        "label": sa_doc.label
    })
    if curr_doc_dict is None:
        return __insert_one_sample_annotation(sa_doc, db)

    curr_doc = SampleAnnotationDoc(**curr_doc_dict)
    assert curr_doc.id is not None
    new_labels = {sample.label for sample in sa_doc.samples}
    curr_labels = {sample.label for sample in curr_doc.samples}
    samples_to_insert = [
        sample for sample in sa_doc.samples
        if sample.label not in (new_labels & curr_labels)
    ]
    return __update_one_sample_annotation(curr_doc.id, samples_to_insert, db)


def __insert_one_sample_annotation(
    sa_doc: SampleAnnotationDoc,
    db: Database
) -> SampleAnnotationOut:
    SA_COLL = get_collection(SampleAnnotationDoc, db)
    sa_doc.avg_tpm = round(
        sum([sample.tpm for sample in sa_doc.samples]) / len(sa_doc.samples),
        settings.N_DECIMALS
    )
    to_insert = sa_doc.dict(exclude_none=True)
    _ = SA_COLL.insert_one(to_insert)
    return SampleAnnotationOut(**to_insert)


def __update_one_sample_annotation(
    id: ObjectId,
    new_samples: list[Sample],
    db: Database
) -> SampleAnnotationOut:
    SA_COLL = get_collection(SampleAnnotationDoc, db)
    new_samples_dict = [new_sample.dict(exclude_none=True) for new_sample in new_samples]
    result = SA_COLL.find_one_and_update(
        filter={"_id": id},
        update={"$push": {"samples": {"$each": new_samples_dict}}}
    )
    new_avg_tpm = SA_COLL.aggregate([
        {"$match": {"_id": id}},
        {"$unwind": "$samples"},
        {"$group": {"_id": "$_id", "avgTpm": {"$avg": "$samples.tpm"}}}
    ]).next()["avgTpm"]
    result = SA_COLL.find_one_and_update(
        filter={"_id": id},
        update={"$set": {"avg_tpm": new_avg_tpm}}
    )
    return SampleAnnotationOut(**result)


def update_affected_spm(
    species_id: ObjectId,
    gene_id: ObjectId,
    annotation_type: str,
    db: Database
) -> None:
    # Only called when all the SA docs avg_tpm have been updated
    SA_COLL = get_collection(SampleAnnotationDoc, db)
    sa_dicts = SA_COLL.find({
        "spe_id": species_id,
        "g_id": gene_id,
        "type": annotation_type,
    })
    sa_docs = [SampleAnnotationDoc(**sa_dict) for sa_dict in sa_dicts]
    total_avg_tpm = round(sum([sa_doc.avg_tpm for sa_doc in sa_docs]), settings.N_DECIMALS)
    for sa_doc in sa_docs:
        if total_avg_tpm == 0:
            sa_doc.spm = 0
        else:
            sa_doc.spm = round(sa_doc.avg_tpm / total_avg_tpm, settings.N_DECIMALS)
        _ = SA_COLL.update_one(
            {"_id": sa_doc.id},
            {"$set": {"spm": sa_doc.spm}}
        )


# # DEPRECATED
# def insert_many_sample_annotations(
#     sa_docs: list[SampleAnnotationDoc],
#     db: Database
# ) -> list[SampleAnnotationOut]:
#     SA_COLL = get_collection(SampleAnnotationDoc, db)
#     to_insert = [sa_doc.dict(exclude_none=True) for sa_doc in sa_docs]
#     try:
#         result = SA_COLL.insert_many(
#             to_insert,
#             ordered=False
#         )
#         pointer = SA_COLL.find({
#             "_id": {"$in": result.inserted_ids}
#         })
#         return [SampleAnnotationOut(**doc) for doc in pointer]
#     except BulkWriteError as e:
#         print(f"Only {e.details['nInserted']} / {len(to_insert)} sample annotations are newly inserted into the sample annotations collection")
#         print(f"writeErrors: {e.details['writeErrors']}")
#         # Return only newly inserted documents
#         existing_ids = [doc['op']['_id'] for doc in e.details['writeErrors']]
#         to_insert_ids = [doc['_id'] for doc in to_insert]
#         new_ids = list(set(to_insert_ids) - set(existing_ids))
#         pointer = SA_COLL.find({
#             "_id": {"$in": new_ids}
#         })
#         return [SampleAnnotationOut(**doc) for doc in pointer]
