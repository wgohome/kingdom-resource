from pydantic import Field

from .shared import PyObjectId, CustomBaseModel, DocumentBaseModel


class GeneBase(CustomBaseModel):
    id: PyObjectId | None = Field(alias="_id")
    spe_id: PyObjectId | None = Field(alias="species_id")
    label: str
    #   label refers to the main gene identifier we use in the TPM matrix
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
    spe_id: PyObjectId = Field(alias="species_id")


class GeneDoc(GeneBase, DocumentBaseModel):
    spe_id: PyObjectId = Field(alias="species_id")

    class Mongo:
        collection_name: str = "genes"
