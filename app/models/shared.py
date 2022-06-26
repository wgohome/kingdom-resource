import warnings
from bson import ObjectId
from pydantic import BaseModel, Extra, Field, validator


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


#
# For all models
#
class CustomBaseModel(BaseModel):
    class Config:
        allow_population_by_field_name = True
        #   Warning for potential leakages of attributes
        #   Acceptable risks for now
        json_encoders = {ObjectId: str}
        #   Note that we encode ObjectId, not PyObjectId because
        #   that is how we decode it in validate classmethod
        extra = Extra.forbid

    # For dict to be dumped into DB for creation
    def dict_for_db(self) -> dict:
        # `exclude_none=True` allows
        # - downstream models to set the default values themselves
        # - not to store redudant fields (eg in polymorphic models)
        # `by_alias=False` as
        # - as we define field names as db keys, and alias as client facing keys
        #   as recommended by Samuel Colvin (Pydantic owner)
        return self.dict(exclude_none=True, by_alias=False)

    # For dict to be dumped into DB for update of set fields only
    def dict_for_update(self) -> dict:
        # To avoid overriding existing fields in the DB with default values on update
        return self.dict(exclude_unset=True, by_alias=True)


#
# Only for models representing DB document schema
#
class DocumentBaseModel(BaseModel):
    class Mongo:
        collection_name: str


#
# Super class for response model with pagination
#   for use with multiple inheritance
#
class BasePageModel(CustomBaseModel):
    page_total: int = Field(ge=0)
    curr_page: int = Field(ge=0)
    payload: list[CustomBaseModel]  # to be overriden in subclass

    # NOTE: Leaving validation out bcos
    #   we still want to tell client how many pages there are in total
    #   just return an empty array
    # @validator("curr_page")
    # def curr_page_fewer_than_total(cls, v, values):
    #     if v > values["page_total"]:
    #         raise ValueError("`curr_page` must be at most `page_total`")
    #     return v

    # Method Overriden
    def dict_for_db(self) -> dict:
        warnings.warn("Not expecting to store paginated arrays to DB as it is")
        return super().dict_for_db()

    # Method Overriden
    def dict_for_update(self) -> dict:
        warnings.warn("Not expecting to store paginated arrays to DB as it is")
        return super().dict_for_update()
