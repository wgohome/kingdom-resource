from datetime import datetime
from pydantic import Field
from typing import Optional

from .shared import PyObjectId, CustomBaseModel, DocumentBaseModel

#
# Class naming conventions
#   SpeciesBase: the base attributes, as parent class to be inherited
#   SpeciesDoc: attributes matching document schema in DB
#   SpeciesIn: attributes for new object instantiation
#   SpeciesOut: attributes for returning objects as payload
#


class Cds(CustomBaseModel):
    source: str  # Eg: "Ensembl"
    url: Optional[str] = None


class QcStat(CustomBaseModel):
    logp: float = Field(0, alias="log_processed")
    palgn: int = Field(0, alias="p_pseudoaligned", ge=0, le=100)


class SpeciesBase(CustomBaseModel):
    tax: int = Field(alias="taxid")
    #   taxid indexed for search by taxid
    name: str
    alias: list[str] = list()  # Must be a factory for mutable objects
    cds: "Cds"
    qc_stat: QcStat = Field(default_factory=QcStat)
    n_genes: int = Field(default=0, ge=0)
    n_samples: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SpeciesIn(SpeciesBase):
    pass


class SpeciesOut(SpeciesBase):
    id: PyObjectId | None = Field(alias="_id")


class SpeciesDoc(SpeciesBase, DocumentBaseModel):
    id: PyObjectId | None = Field(alias="_id")

    class Mongo:
        collection_name: str = "species"


SpeciesBase.update_forward_refs()
