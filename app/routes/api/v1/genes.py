from bson import ObjectId
from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.db.setup import get_db
from app.db.genes_collection import (
    find_all_genes_by_species,
    enforce_no_existing_genes,
    enforce_no_existing_genes,
    insert_many_genes,
)
from app.db.species_collection import (
    find_species_id_from_taxid,
)
from app.models.genes import GeneOut, GeneIn, GeneProcessed

router = APIRouter(prefix="/api/v1", tags=["genes"])


@router.get(
    "/species/{taxid}/genes",
    response_model=list[GeneOut]
)
def get_all_genes_of_a_species(taxid: int, db: Database = Depends(get_db)):
    species_id: ObjectId = find_species_id_from_taxid(taxid, db)
    return find_all_genes_by_species(species_id, db)


@router.post(
    "/species/{taxid}/genes",
    status_code=201,
    response_model=list[GeneOut]
)
def post_many_genes_by_species(
    genes_in: list[GeneIn],
    taxid: int,
    skip_duplicates: bool = False,
    db: Database = Depends(get_db)
):
    if skip_duplicates is False:
        enforce_no_existing_genes(genes_in, db)
    species_id: ObjectId = find_species_id_from_taxid(taxid, db)
    genes_processed: list[GeneProcessed] = [
        GeneProcessed(
            **gene_in.dict(by_alias=True, exclude_none=True),
            species_id=species_id
        )
        for gene_in in genes_in
    ]
    inserted_genes = insert_many_genes(genes_processed, db)
    return inserted_genes
