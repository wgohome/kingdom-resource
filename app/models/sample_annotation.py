from pydantic import Field, validator

from .shared import PyObjectId, CustomBaseModel, DocumentBaseModel

#
# Class naming conventions
#   SampleAnnotationBase: the base attributes, as parent class to be inherited
#   SampleAnnotationDoc: attributes matching document schema in DB
#   SampleAnnotationInput: attributes for the body to be accepted in the post request
#   SampleAnnotationOut: attributes for returning objects as payload
#


class Sample(CustomBaseModel):
    lbl: str = Field(alias="sample_label")
    tpm: float = Field(alias="tpm_value")

    @validator("lbl", pre=True)
    def upcase_lbl(cls, v):
        return v.upper()


class SampleAnnotationBase(CustomBaseModel):
    spe_id: PyObjectId = Field(alias="species_id")
    g_id: PyObjectId = Field(alias="gene_id")
    type: str = Field(alias="annotation_type")
    lbl: str = Field(alias="annotation_label")
    spm: float = 0
    avg_tpm: float = 0
    samples: list[Sample]

    @validator("type", pre=True)
    def upcase_type(cls, v):
        return v.upper()

    @validator("lbl", pre=True)
    def upcase_lbl(cls, v):
        return v.upper()


class SampleAnnotationRow(CustomBaseModel):  # tpm row not sample annotation
    annotation_label: str
    sample_label: str
    tpm: float


class SampleAnnotationInput(CustomBaseModel):
    species_taxid: int
    gene_label: str  # Main Gene Identifier used for this db
    anontation_type: str  # Eg, Mapman annotations, GO, etc
    rows: list[SampleAnnotationRow]


# class SampleAnnotationProcessed(SampleAnnotationBase):
#     pass


class SampleAnnotationOut(SampleAnnotationBase):
    id: PyObjectId | None = Field(alias="_id")


class SampleAnnotationDoc(SampleAnnotationBase, DocumentBaseModel):
    id: PyObjectId | None = Field(alias="_id")

    class Mongo:
        collection_name: str = "sample_annotations"
