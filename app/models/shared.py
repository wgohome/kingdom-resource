from bson import ObjectId
from pydantic import BaseModel


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class CustomBaseModel(BaseModel):
    class Config:
        # extra = "forbid"
        allow_population_by_field_name = True
        # arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        #   Note that we encode ObjectId, not PyObjectId because
        #   that is how we decode it in validate classmethod


class DocumentBaseModel(BaseModel):
    class Mongo:
        collection_name: str
