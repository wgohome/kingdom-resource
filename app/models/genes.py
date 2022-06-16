from pydantic import Field

from .shared import PyObjectId, CustomBaseModel, DocumentBaseModel

#
# Class naming conventions
#   GeneBase: the base attributes, as parent class to be inherited
#   GeneDoc: attributes matching document schema in DB
#   GeneIn: attributes for the body to be accepted in the post request
#   GeneProcessed: converting GeneIn attributes for new object instantiation
#   GeneOut: attributes for returning objects as payload
#


class GeneBase(CustomBaseModel):
    spe_id: PyObjectId | None = Field(alias="species_id")
    label: str
    #   label refers to the main gene identifier we use in the TPM matrix
    #   indexed for search by label
    alias: list[str] = list()
    #   alias - other alternative gene identifiers
    name: str
    #   name refers to the human-readable name of the gene
    desc: str = Field(alias="description")
    #   Only single set of gene annotation name and description accomodated for now
    sa_ids: list[PyObjectId] = Field(default_factory=list, alias="sample_annotation_ids")
    #   this list will be bounded as the number of annotation class bins will not grow indefinitely,
    #   ~20 labels now from student annotation project


class GeneIn(GeneBase):
    pass


class GeneProcessed(GeneBase):
    spe_id: PyObjectId = Field(alias="species_id")


class GeneOut(GeneBase):
    id: PyObjectId | None = Field(alias="_id")
    spe_id: PyObjectId = Field(alias="species_id")


class GeneDoc(GeneBase, DocumentBaseModel):
    id: PyObjectId | None = Field(alias="_id")
    spe_id: PyObjectId = Field(alias="species_id")

    class Mongo:
        collection_name: str = "genes"
