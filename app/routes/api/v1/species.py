from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.db.setup import get_db
from app.db.species_collection import (
    delete_one_species,
    enforce_no_existing_species_in_list,
    enforce_taxid_not_exist,
    find_all_species,
    find_species_id_from_taxid,
    find_one_species_by_taxid,
    insert_many_species,
    insert_one_species,
    insert_or_replace_many_species,
    update_one_species,
)
from app.models.species import (
    SpeciesIn,
    SpeciesOut,
    SpeciesPage,
    SpeciesUpdate,
    SpeciesUpdateIn,
)

router = APIRouter(prefix="/api/v1", tags=["species"])


@router.get("/species", response_model=SpeciesPage)
def get_all_species(page_num: int = 1, db: Database = Depends(get_db)):
    return find_all_species(page_num=page_num, db=db)


@router.get("/species/{taxid}", response_model=SpeciesOut)
def get_one_species_by_taxid(taxid: int, db: Database = Depends(get_db)):
    return find_one_species_by_taxid(taxid, db)


@router.post(
    "/species",
    status_code=201,
    response_model=SpeciesOut
)
def post_one_species(
    species_in: SpeciesIn,
    db: Database = Depends(get_db)
):
    enforce_taxid_not_exist(species_in.tax, db)
    return insert_one_species(species_in, db)


@router.post(
    "/species/batch",
    status_code=201,
    response_model=list[SpeciesOut]
)
def post_many_species(
    species_in_list: list[SpeciesIn],
    skip_duplicates: bool = False,
    db: Database = Depends(get_db),
):
    if skip_duplicates is False:
        enforce_no_existing_species_in_list(species_in_list, db)
    inserted_species = insert_many_species(species_in_list, db)
    return inserted_species


@router.put("/species/batch", status_code=200, response_model=list[SpeciesOut])
def put_many_species(species_in_list: list[SpeciesIn], db: Database = Depends(get_db)):
    return insert_or_replace_many_species(species_in_list, db)


@router.delete("/species/{taxid}", status_code=200, response_model=SpeciesOut)
def delete_species(taxid: int, db: Database = Depends(get_db)):
    # TODO delete associated resources
    return delete_one_species(taxid, db)


@router.patch("/species/{taxid}", status_code=200, response_model=SpeciesOut)
def update_species(
    taxid: int,
    update_form: SpeciesUpdateIn,
    db: Database = Depends(get_db)
):
    species_id = find_species_id_from_taxid(taxid, db)
    update_fields = SpeciesUpdate(**update_form.dict(exclude_unset=True))
    return update_one_species(species_id, update_fields, db)
