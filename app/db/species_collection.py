from app.db.setup import get_collection

from app.models.species import SpeciesDoc, SpeciesIn, SpeciesOut

SPECIES_COLL = get_collection(SpeciesDoc)


def find_all_species():
    return [
        SpeciesOut(**species_dict)
        for species_dict in SPECIES_COLL.find()
    ]


def insert_many_species(species_in_list: list[SpeciesIn]):
    result = SPECIES_COLL.insert_many(
        [sp_in.dict(exclude_none=True) for sp_in in species_in_list],
        ordered=False
    )
    pointer = SPECIES_COLL.find({
        "_id": {"$in": result.inserted_ids}
    })
    return [SpeciesOut(**doc) for doc in pointer]
