from collections import defaultdict
from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.db.gene_annotations_collection import (
    check_if_ga_exists,
    convert_ga_in_to_ga_proc,
    delete_one_ga,
    enforce_no_existing_ga,
    enforce_no_existing_gas,
    find_all_gas,
    find_one_ga,
    insert_one_ga,
    insert_one_new_ga_or_append_gene_ids,
    insert_or_replace_many_gas,
    update_one_ga,
)
from app.db.genes_collection import add_annotations_to_gene
from app.db.setup import get_db
from app.db.users_collection import verify_api_key
from app.models.gene_annotation import (
    GeneAnnotationIn,
    GeneAnnotationOut,
    GeneAnnotationPage,
    GeneAnnotationUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["gene_annotations"])
private_router = APIRouter(dependencies=[Depends(verify_api_key)])


# TODO: implement this as an PATCH request instead
# @router.post(
#     "species/{taxid}/gene_annotations",
#     status_code=201,
#     response_model=GeneAnnotationOut
# )
# def post_many_gene_annotations(
#     taxid: int,
#     ga_in: GeneAnnotationInput,
#     db: Database = Depends(get_db)
# ):
#     species_id: PyObjectId = find_species_id_from_taxid(taxid, db)
#     # Get all gene ids of this species
#     # Map each row's gene labels to gene ids, if gene label not found throw 404
#     # Group rows by Annotation type + label
#     # If doc not found, create new ga doc, with gene ids added as fields
#     # If gene_id(s) not already in existing doc, append to list
#     # 2 way rs, also need to record ga id in gene doc


@router.get("/gene_annotations", response_model=GeneAnnotationPage)
def get_all_gene_annotations(
    type: str | None = None,
    label: str | None = None,
    page_num: int = 1,
    db: Database = Depends(get_db)
):
    return find_all_gas(page_num, db, type, label)


@router.get(
    "/gene_annotations/type/{type}/label/{label}",
    response_model=GeneAnnotationOut
)
def get_one_gene_annotation(type: str, label: str, db: Database = Depends(get_db)):
    return find_one_ga(type, label, db)


@private_router.post(
    "/gene_annotations",
    status_code=201,
    response_model=GeneAnnotationOut
)
def post_one_gene_annotation(ga_in: GeneAnnotationIn, db: Database = Depends(get_db)):
    # check duplicates
    enforce_no_existing_ga(ga_in, db)
    ga_proc = convert_ga_in_to_ga_proc(ga_in, db)
    ga_out = insert_one_ga(ga_proc, db)
    return ga_out


@private_router.post(
    "/gene_annotations/batch",
    status_code=201,
    response_model=list[GeneAnnotationOut]
)
def post_many_gene_annotations(
    ga_input: list[GeneAnnotationIn],
    skip_duplicates: bool = False,
    db: Database = Depends(get_db)
):
    if skip_duplicates is False:
        enforce_no_existing_gas(ga_input, db)
    gas_out = []
    genes_update = defaultdict(list)
    for ga_in in ga_input:
        ga_proc = convert_ga_in_to_ga_proc(ga_in, db)
        if check_if_ga_exists(ga_in.type, ga_in.label, db) is False:
            ga_out = insert_one_ga(ga_proc, db)
            gas_out.append(ga_out)
            for gene_id in ga_proc.gene_ids:
                genes_update[gene_id] = list(set(genes_update[gene_id]) & set(str(ga_out.id)))
    for gene_id, ga_ids in genes_update.items():
        add_annotations_to_gene(gene_id, ga_ids, db)
    return gas_out


@private_router.put(
    "/gene_annotations/batch",
    status_code=200,
    response_model=list[GeneAnnotationOut]
)
def put_many_gene_annotations(
    ga_input: list[GeneAnnotationIn],
    db: Database = Depends(get_db)
):
    ga_procs = [convert_ga_in_to_ga_proc(ga_in, db) for ga_in in ga_input]
    return insert_or_replace_many_gas(ga_procs, db)


#
# Upsert-like operation
# For each GeneAnnotationIn in the array
#   - If GeneAnnotationDoc not present yet,
#       - Insert the doc to DB
#       - Append the updated doc to the response model array
#   - Otherwise, find the existing GeneAnnotationDoc
#       - Take taxid + gene labels combi that are not already embedded in the doc
#       - Append to the genes array in the doc
#       - Append the updated doc to the response model array
#
@private_router.patch(
    "/gene_annotations/batch",
    status_code=200,
    response_model=list[GeneAnnotationOut]
)
def add_genes_to_gene_annotations(
    ga_input: list[GeneAnnotationIn],
    db: Database = Depends(get_db)
):
    ga_procs = [convert_ga_in_to_ga_proc(ga_in, db) for ga_in in ga_input]
    return [
        insert_one_new_ga_or_append_gene_ids(ga_proc, db)
        for ga_proc in ga_procs
    ]


@private_router.delete(
    "/gene_annotations/type/{ga_type}/label/{label}",
    status_code=200,
    response_model=GeneAnnotationOut
)
def delete_gene_annotation(ga_type: str, label: str, db: Database = Depends(get_db)):
    # TODO remove association from assocaited gene docs
    return delete_one_ga(ga_type, label, db)


@private_router.patch(
    "/gene_annotations/type/{ga_type}/label/{label}",
    status_code=200,
    response_model=GeneAnnotationOut
)
def update_gene_annotation(
    ga_type: str,
    label: str,
    update_form: GeneAnnotationUpdate,
    db: Database = Depends(get_db)
):
    return update_one_ga(ga_type, label, update_form, db)


router.include_router(private_router)
