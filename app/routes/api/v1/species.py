from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.db.setup import get_db
from app.db.species_collection import (
    find_all_species,
    insert_many_species,
    find_one_species_by_taxid
)
from app.models.species import SpeciesIn, SpeciesOut

router = APIRouter(prefix="/api/v1", tags=["species"])


@router.get("/species", response_model=list[SpeciesOut])
def get_all_species(db = Depends(get_db)):
    return find_all_species(db)


@router.post("/species", status_code=201, response_model=list[SpeciesOut])
def post_many_species(species_in_list: list[SpeciesIn], db: Database = Depends(get_db)):
    # check_no_existing_species()
    inserted_species = insert_many_species(species_in_list, db)
    return inserted_species


@router.get("/species/{taxid}", response_model=SpeciesOut)
def get_one_species_by_taxid(taxid: int, db: Database = Depends(get_db)):
    return find_one_species_by_taxid(taxid, db)
