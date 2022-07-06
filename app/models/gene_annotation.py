from pydantic import Field, validator

from .shared import BasePageModel, PyObjectId, CustomBaseModel, DocumentBaseModel


# class GeneAnnotationRow(CustomBaseModel):
#     gene_label: str
#     label: str | None  # Annotation identifier
#     details: dict | None = Field(alias="details")


# class GeneAnnotationInput(CustomBaseModel):
#     type: str  # Annotation type, eg Gene Ontology, Mapman
#     rows: list[GeneAnnotationRow]


# class GeneAnnotationProcessed(CustomBaseModel):
#     type: str  # Annotation type, eg Gene Ontology, Mapman
#     label: str | None  # Annotation identifier to be indexed for uniqueness with type
#     details: dict | None = Field(alias="details")


class GeneInput(CustomBaseModel):
    taxid: int
    gene_label: str

    @validator("gene_label", pre=True)
    def upcase_gene_label(cls, v):
        return v.upper()


class GeneAnnotationBase(CustomBaseModel):
    type: str  # Annotation type, eg Gene Ontology, Mapman
    label: str   # Annotation identifier to be indexed for uniqueness with type
    details: dict | None

    @validator("type", pre=True)
    def upcase_type(cls, v):
        return v.upper()

    @validator("label", pre=True)
    def upcase_label(cls, v):
        return v.upper()


class GeneAnnotationUpdate(GeneAnnotationBase):
    pass


class GeneAnnotationIn(GeneAnnotationBase):
    genes: list[GeneInput] = list()


class GeneAnnotationProcessed(GeneAnnotationBase):
    gene_ids: list[PyObjectId] = list()


class GeneAnnotationOut(GeneAnnotationProcessed):
    id: PyObjectId = Field(alias="_id")


class GeneAnnotationPage(BasePageModel):
    payload: list[GeneAnnotationOut]


class GeneAnnotationDoc(GeneAnnotationProcessed, DocumentBaseModel):
    id: PyObjectId = Field(alias="_id")

    class Mongo:
        collection_name: str = "gene_annotations"
