from fastapi import APIRouter

from ....models.species import SpeciesDoc, SpeciesIn

router = APIRouter(prefix="/api/v1", tags=["species"])


@router.get("/species", response_model=list[SpeciesDoc])
def get_all_species():
    return []


@router.post("/species", response_model=list[SpeciesDoc])
def post_many_species(species_in_list: list[SpeciesIn]):
    return []
