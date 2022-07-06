from pydantic import Field

from .shared import BasePageModel, PyObjectId, CustomBaseModel, DocumentBaseModel

#
# Class naming conventions
#   GeneBase: the base attributes, as parent class to be inherited
#   GeneDoc: attributes matching document schema in DB
#   GeneIn: attributes for the body to be accepted in the post request
#   GeneProcessed: converting GeneIn attributes for new object instantiation
#   GeneOut: attributes for returning objects as payload
#


class GeneIn(CustomBaseModel):
    label: str
    #   label refers to the main gene identifier we use in the TPM matrix
    #   indexed for search by label
    alias: list[str] = list()
    #   alias - other alternative gene identifiers


class GeneProcessed(GeneIn):
    spe_id: PyObjectId = Field(alias="species_id")
    anots: list[PyObjectId] = Field(default_factory=list, alias="annotations")
    #   reference to gene_annotations collection


class GeneUpdate(GeneIn):
    anots: list[PyObjectId] = Field(default_factory=list, alias="annotations")


class GeneBase(GeneProcessed):
    id: PyObjectId | None = Field(alias="_id")


class GeneOut(GeneBase):
    pass


class GenePage(BasePageModel):
    payload: list[GeneOut]


class GeneDoc(GeneBase, DocumentBaseModel):
    class Mongo:
        collection_name: str = "genes"
