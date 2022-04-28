from pymongo.database import Database
from pydantic.main import ModelMetaclass

from app.models.species import SpeciesDoc, SpeciesIn, SpeciesOut


def __get_collection(model: ModelMetaclass, db):
    assert hasattr(model, "Mongo"), "ModelMetaclass should inherit from DocumentBaseModel"
    return db[model.Mongo.collection_name]  # type: ignore


def find_all_species(db: Database):
    SPECIES_COLL = __get_collection(SpeciesDoc, db)
    return [
        SpeciesOut(**species_dict)
        for species_dict in SPECIES_COLL.find()
    ]


def insert_many_species(species_in_list: list[SpeciesIn], db: Database):
    SPECIES_COLL = __get_collection(SpeciesDoc, db)
    result = SPECIES_COLL.insert_many(
        [sp_in.dict(exclude_none=True) for sp_in in species_in_list],
        ordered=False
    )
    pointer = SPECIES_COLL.find({
        "_id": {"$in": result.inserted_ids}
    })
    return [SpeciesOut(**doc) for doc in pointer]


def find_one_species_by_taxid(taxid: int, db: Database):
    SPECIES_COLL = __get_collection(SpeciesDoc, db)
    species_dict = SPECIES_COLL.find_one({
        "tax": taxid
    })
    # TODO: raise 404 not found if taxid not found
    return species_dict
