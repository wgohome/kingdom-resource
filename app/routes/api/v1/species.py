from fastapi import APIRouter

from app.db.species_collection import (
    find_all_species,
    insert_many_species
)
from app.models.species import SpeciesIn, SpeciesOut

router = APIRouter(prefix="/api/v1", tags=["species"])


@router.get("/species", response_model=list[SpeciesOut])
def get_all_species():
    return find_all_species()


@router.post("/species", status_code=201, response_model=list[SpeciesOut])
def post_many_species(species_in_list: list[SpeciesIn]):
    # check_no_existing_species()
    inserted_species = insert_many_species(species_in_list)
    return inserted_species
