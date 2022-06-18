from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.db.setup import get_db
from app.db.species_collection import (
    delete_one_species,
    find_all_species,
    insert_many_species,
    find_one_species_by_taxid,
    enforce_no_existing_species
)
from app.models.species import SpeciesIn, SpeciesOut

router = APIRouter(prefix="/api/v1", tags=["species"])


@router.get("/species", response_model=list[SpeciesOut])
def get_all_species(db: Database = Depends(get_db)):
    return find_all_species(db)


@router.get("/species/{taxid}", response_model=SpeciesOut)
def get_one_species_by_taxid(taxid: int, db: Database = Depends(get_db)):
    return find_one_species_by_taxid(taxid, db)


@router.post(
    "/species",
    status_code=201,
    response_model=list[SpeciesOut]
)
def post_many_species(
    species_in_list: list[SpeciesIn],
    skip_duplicates: bool = False,
    db: Database = Depends(get_db),
):
    if skip_duplicates is False:
        enforce_no_existing_species(species_in_list, db)
    inserted_species = insert_many_species(species_in_list, db)
    return inserted_species


@router.delete("/species/{taxid}", status_code=200, response_model=SpeciesOut)
def delete_species(taxid: int, db: Database = Depends(get_db)):
    # TODO delete associated resources
    return delete_one_species(taxid, db)
