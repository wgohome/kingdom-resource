from pydantic import Field

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


class GeneAnnotationBase(CustomBaseModel):
    type: str  # Annotation type, eg Gene Ontology, Mapman
    label: str   # Annotation identifier to be indexed for uniqueness with type
    details: dict | None


class GeneAnnotationUpdate(GeneAnnotationBase):
    pass


class GeneAnnotationIn(GeneAnnotationBase):
    gene_labels: list[str] = list()


class GeneAnnotationProcessed(GeneAnnotationBase):
    gene_ids: list[PyObjectId] = list()


class GeneAnnotationOut(GeneAnnotationProcessed):
    id: PyObjectId | None = Field(alias="_id")


class GeneAnnotationPage(BasePageModel):
    payload: list[GeneAnnotationOut]


class GeneAnnotationDoc(GeneAnnotationProcessed, DocumentBaseModel):
    id: PyObjectId | None = Field(alias="_id")

    class Mongo:
        collection_name: str = "gene_annotations"
