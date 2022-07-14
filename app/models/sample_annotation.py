from pydantic import Field, validator

from .shared import BasePageModel, PyObjectId, CustomBaseModel, DocumentBaseModel

#
# Class naming conventions
#   SampleAnnotationBase: the base attributes, as parent class to be inherited
#   SampleAnnotationDoc: attributes matching document schema in DB
#   SampleAnnotationInput: attributes for the body to be accepted in the post request
#   SampleAnnotationOut: attributes for returning objects as payload
#


class Sample(CustomBaseModel):
    label: str = Field(alias="sample_label")
    tpm: float = Field(alias="tpm_value")

    @validator("label", pre=True)
    def upcase_label(cls, v):
        return v.upper()


class SampleAnnotationBase(CustomBaseModel):
    spe_id: PyObjectId = Field(alias="species_id")
    g_id: PyObjectId = Field(alias="gene_id")
    type: str
    label: str
    spm: float = 0
    avg_tpm: float = 0
    samples: list[Sample]

    @validator("type", pre=True)
    def upcase_type(cls, v):
        return v.upper()

    @validator("label", pre=True)
    def upcase_label(cls, v):
        return v.upper()


class SampleAnnotationUnit(CustomBaseModel):  # tpm row not sample annotation
    annotation_label: str
    sample_label: str
    tpm: float


class SampleAnnotationInput(CustomBaseModel):
    species_taxid: int
    gene_label: str  # Main Gene Identifier used for this db
    annotation_type: str  # Eg, Mapman annotations, GO, etc
    samples: list[SampleAnnotationUnit]


class SampleAnnotationOut(SampleAnnotationBase):
    id: PyObjectId | None = Field(alias="_id")


class SampleAnnotationPage(BasePageModel):
    payload: list[SampleAnnotationOut]


class SampleAnnotationDoc(SampleAnnotationBase, DocumentBaseModel):
    id: PyObjectId | None = Field(alias="_id")

    class Mongo:
        collection_name: str = "sample_annotations"
