from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.db.setup import get_db
from app.db.genes_collection import (
    delete_one_gene,
    find_all_genes_by_species,
    enforce_no_existing_genes,
    find_one_gene_by_label,
    insert_many_genes,
    insert_one_gene,
    insert_or_replace_many_genes,
    update_one_gene,
)
from app.db.species_collection import (
    find_species_id_from_taxid,
)
from app.models.gene import (
    GeneOut,
    GeneIn,
    GenePage,
    GeneProcessed,
)

from app.models.shared import PyObjectId

router = APIRouter(prefix="/api/v1", tags=["genes"])


@router.get("/species/{taxid}/genes", response_model=GenePage)
def get_all_genes_of_a_species(taxid: int, page_num: int = 1, db: Database = Depends(get_db)):
    species_id: PyObjectId = find_species_id_from_taxid(taxid, db)
    return find_all_genes_by_species(species_id, page_num, db)


@router.get("/species/{taxid}/genes/{gene_label}", response_model=GeneOut)
def get_one_gene(taxid: int, gene_label: str, db: Database = Depends(get_db)):
    species_id: PyObjectId = find_species_id_from_taxid(taxid, db)
    return find_one_gene_by_label(species_id, gene_label, db)


@router.post(
    "/species/{taxid}/genes",
    status_code=201,
    response_model=GeneOut
)
def post_one_gene(
    taxid: int,
    gene_in: GeneIn,
    db: Database = Depends(get_db)
):
    species_id: PyObjectId = find_species_id_from_taxid(taxid, db)
    enforce_no_existing_genes(species_id, [gene_in], db)
    gene_processed = GeneProcessed(species_id=species_id, **gene_in.dict_for_db())
    return insert_one_gene(gene_processed, db)


@router.post(
    "/species/{taxid}/genes/batch",
    status_code=201,
    response_model=list[GeneOut]
)
def post_many_genes_by_species(
    taxid: int,
    genes_in: list[GeneIn],
    skip_duplicates: bool = False,
    db: Database = Depends(get_db)
):
    species_id: PyObjectId = find_species_id_from_taxid(taxid, db)
    if skip_duplicates is False:
        enforce_no_existing_genes(species_id, genes_in, db)
    genes_processed: list[GeneProcessed] = [
        GeneProcessed(
            **gene_in.dict(by_alias=True, exclude_none=True),
            species_id=species_id
        )
        for gene_in in genes_in
    ]
    inserted_genes = insert_many_genes(genes_processed, db)
    return inserted_genes


@router.put("/species/{taxid}/genes/batch", status_code=200, response_model=list[GeneOut])
def put_many_genes_by_species(
    taxid: int,
    genes_in_list: list[GeneIn],
    db: Database = Depends(get_db)
):
    species_id = find_species_id_from_taxid(taxid, db)
    return insert_or_replace_many_genes(species_id, genes_in_list, db)


@router.delete(
    "/species/{taxid}/genes/{gene_label}",
    status_code=200,
    response_model=GeneOut
)
def delete_gene(taxid: int, gene_label: str, db: Database = Depends(get_db)):
    # TODO delete associated resources
    return delete_one_gene(taxid, gene_label, db)


@router.patch("/species/{taxid}/genes/{gene_label}", status_code=200, response_model=GeneOut)
def update_species(
    taxid: int,
    gene_label: str,
    update_form: GeneIn,
    db: Database = Depends(get_db)
):
    species_id = find_species_id_from_taxid(taxid, db)
    return update_one_gene(species_id, gene_label, update_form, db)
