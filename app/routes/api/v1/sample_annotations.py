from bson import ObjectId
from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.db.setup import get_db
from app.db.users_collection import verify_api_key
from app.models.sample_annotation import (
    SampleAnnotationInput,
    SampleAnnotationOut,
    SampleAnnotationPage,
)
from app.db.genes_collection import find_gene_id_from_label
from app.db.species_collection import find_species_id_from_taxid
from app.db.sample_annotations_collection import (
    enforce_no_existing_samples_for_gene,
    find_sample_annotations_by_gene,
    find_sample_annotations_by_label,
    insert_or_update_one_sa_doc,
    reshape_sa_input_to_sa_docs,
    update_affected_spm,
)

router = APIRouter(prefix="/api/v1", tags=["sample_annotations"])
private_router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get(
    "/sample_annotations/species/{taxid}/genes/{gene_label}",
    response_model=SampleAnnotationPage
)
def get_sample_annotations_by_gene(
    taxid: int,
    gene_label: str,
    page_num: int = 1,
    db: Database = Depends(get_db)
):
    species_id: ObjectId = find_species_id_from_taxid(taxid, db)
    gene_id: ObjectId = find_gene_id_from_label(species_id, gene_label, db)
    return find_sample_annotations_by_gene(species_id, gene_id, page_num, db)


# Find all sample annotations belonging to a specific label (organ)
#   TODO: future work, specify which clade of interest,
#   return only for species within that clade
@router.get(
    "/sample_annotations/types/{type}/labels/{label}",
    response_model=SampleAnnotationPage
)
def get_sample_annotations_by_label(
    type: str,
    label: str,
    page_num: int = 1,
    db: Database = Depends(get_db)
):
    return find_sample_annotations_by_label(type, label, page_num, db)


@private_router.post(
    "/sample_annotations",
    status_code=201,
    response_model=list[SampleAnnotationOut]
)
def post_one_row_sample_annotations(
    sa_input: SampleAnnotationInput,
    skip_duplicate_samples: bool = False,
    db: Database = Depends(get_db)
):
    species_id: ObjectId = find_species_id_from_taxid(sa_input.species_taxid, db)
    gene_id: ObjectId = find_gene_id_from_label(species_id, sa_input.gene_label, db)
    if skip_duplicate_samples is False:
        enforce_no_existing_samples_for_gene(sa_input, species_id, gene_id, db)
    sa_docs = reshape_sa_input_to_sa_docs(sa_input, species_id, gene_id)
    sa_outs = [insert_or_update_one_sa_doc(sa_doc, db) for sa_doc in sa_docs]
    update_affected_spm(species_id, gene_id, sa_input.annotation_type, db)
    # TODO return newly queried docs with updated SPM instead
    return sa_outs


@private_router.post(
    "/sample_annotations/batch",
    status_code=201,
    response_model=list[SampleAnnotationOut]
)
def post_many_rows_sample_annotations(
    sa_input_list: list[SampleAnnotationInput],
    skip_duplicate_samples: bool = False,
    db: Database = Depends(get_db)
):
    output = []
    for sa_input in sa_input_list:
        species_id: ObjectId = find_species_id_from_taxid(sa_input.species_taxid, db)
        gene_id: ObjectId = find_gene_id_from_label(species_id, sa_input.gene_label, db)
        if skip_duplicate_samples is False:
            enforce_no_existing_samples_for_gene(sa_input, species_id, gene_id, db)
        sa_docs = reshape_sa_input_to_sa_docs(sa_input, species_id, gene_id)
        sa_outs = [insert_or_update_one_sa_doc(sa_doc, db) for sa_doc in sa_docs]
        update_affected_spm(species_id, gene_id, sa_input.annotation_type, db)
        # TODO return newly queried docs with updated SPM instead
        output += sa_outs
    return output


router.include_router(private_router)
