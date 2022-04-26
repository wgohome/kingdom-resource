from datetime import date
from pydantic import BaseModel, Field
from typing import Optional


class SpeciesDoc(BaseModel):
    tax: int = Field(alias="taxanomic_label")
    name: str
    alias: list[str]
    cds: "Cds"
    qc_stats: "QcStats"
    n_genes: Optional[int] = Field(default=0, ge=0)
    n_samples: Optional[int] = Field(default=0, ge=0)

    class Collection:
        name = "species"


class Cds(BaseModel):
    url: Optional[str] = None
    source: str
    date: date


class QcStats(BaseModel):
    logp: float = Field(0, alias="log_processed")
    palgn: int = Field(0, alias="p_pseudoaligned", ge=0, le=100)


class SpeciesIn(BaseModel):
    tax: int = Field(alias="taxanomic_label")
    name: str
    alias: list[str] = list()
    cds: "Cds"
    qc_stats: "QcStats"
