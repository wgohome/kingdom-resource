from datetime import datetime
from pydantic import Field
from typing import Optional

from .shared import BasePageModel, PyObjectId, CustomBaseModel, DocumentBaseModel

#
# Class naming conventions
#   SpeciesIn: attributes for data expected in API endpoint
#   SpeciesBase: the base attributes, as parent class to be inherited
#   SpeciesDoc: attributes matching document schema in DB
#   SpeciesOut: attributes for returning objects as payload
#


class Cds(CustomBaseModel):
    source: str  # Eg: "Ensembl"
    url: Optional[str] = None


class QcStat(CustomBaseModel):
    logp: float = Field(0, alias="log_processed")
    palgn: int = Field(0, alias="p_pseudoaligned", ge=0, le=100)


class SpeciesIn(CustomBaseModel):
    tax: int = Field(alias="taxid")
    #   taxid indexed for search by taxid
    name: str
    alias: list[str] = list()  # Must be a factory for mutable objects
    cds: "Cds"


class SpeciesUpdateIn(CustomBaseModel):
    name: str | None
    alias: list[str] | None
    cds: Cds | None


class SpeciesUpdate(SpeciesUpdateIn):
    updated_at: datetime = Field(default_factory=datetime.now)


class SpeciesBase(SpeciesIn):
    id: PyObjectId | None = Field(alias="_id")
    # QC stats should not be set on species creation, but on uploading TPM
    qc_stat: QcStat = Field(default_factory=QcStat)
    # timestamps should not be set by user
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SpeciesOut(SpeciesBase):
    pass


class SpeciesPage(BasePageModel):
    payload: list[SpeciesOut]


class SpeciesDoc(SpeciesBase, DocumentBaseModel):
    class Mongo:
        collection_name: str = "species"


SpeciesBase.update_forward_refs()
