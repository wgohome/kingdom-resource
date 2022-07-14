import json
import math
import pytest
from fastapi import status

from config import settings

#
# FIXTURES
#


@pytest.fixture
def sa_dict_1(one_gene_inserted):
    gene_doc, taxid = one_gene_inserted
    return {
        "species_taxid": taxid,
        "gene_label": gene_doc["label"],
        "annotation_type": "FIRST ANOT TYPE",
        "samples": [
            {
                "annotation_label": "ANOT LABEL A",
                "sample_label": "SAMPLE 1",
                "tpm": 10
            },
            {
                "annotation_label": "ANOT LABEL A",
                "sample_label": "SAMPLE 2",
                "tpm": 5
            },
            {
                "annotation_label": "ANOT LABEL B",
                "sample_label": "SAMPLE 3",
                "tpm": 15
            },
        ]
    }


@pytest.fixture
def many_sa_dics(many_genes_inserted, t_client):
    genes, taxid = many_genes_inserted
    return [
        {
            "species_taxid": taxid,
            "gene_label": gene["label"],
            "annotation_type": "ANOT TYPE SAME",
            "samples": [
                {
                    "annotation_label": "ANOT LABEL A",
                    "sample_label": f"SAMPLE 1-{3000 + i}",
                    "tpm": 10
                },
                {
                    "annotation_label": "ANOT LABEL A",
                    "sample_label": f"SAMPLE 2-{3000 + i}",
                    "tpm": 5
                },
                {
                    "annotation_label": "ANOT LABEL B",
                    "sample_label": f"SAMPLE 3-{3000 + i}",
                    "tpm": 15
                },
            ]
        }
        for i, gene in enumerate(genes)
    ]


@pytest.fixture
def sa_dict_1_inserted(sa_dict_1, t_client):
    response = t_client.post(
        f"/api/v1/sample_annotations?api_key={settings.TEST_API_KEY}",
        json=sa_dict_1
    )
    assert response.status_code == status.HTTP_201_CREATED
    # NOTE: This is list[SampleAnnotationOut]
    return response.json()


@pytest.fixture
def many_sa_dics_inserted(many_sa_dics, t_client):
    response = t_client.post(
        f"/api/v1/sample_annotations/batch?api_key={settings.TEST_API_KEY}",
        json=many_sa_dics
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


#
# TESTS
#


def test_post_one_row_sa_valid(sa_dict_1_inserted, sa_dict_1):
    sas = sa_dict_1_inserted
    # Check correct annotation type
    assert all([sa["type"] == sa_dict_1["annotation_type"] for sa in sas])
    # Check that sample annotations are grouped correctly
    assert len(sas) == 2
    # Check that avg tpm calculated correctly
    assert sas[0]["avg_tpm"] == 7.5
    # TODO check that spm were updated correcly


def test_post_many_rows_sa_valid(many_sa_dics_inserted, many_sa_dics):
    result = many_sa_dics_inserted
    assert len(result) == len(many_sa_dics) * 2


def test_get_ga_by_gene(many_sa_dics_inserted, many_sa_dics, t_client):
    taxid = many_sa_dics[0]["species_taxid"]
    gene_label = many_sa_dics[0]["gene_label"]
    response = t_client.get(
        f"/api/v1/sample_annotations/species/{taxid}/genes/{gene_label}?api_key={settings.TEST_API_KEY}"
    )
    assert response.status_code == status.HTTP_200_OK


def test_get_ga_by_annotation(many_sa_dics_inserted, many_sa_dics, t_client):
    annotation_type = many_sa_dics[0]["annotation_type"]
    annotation_label = many_sa_dics[0]["samples"][0]["annotation_label"]
    response = t_client.get(
        f"/api/v1/sample_annotations/types/{annotation_type}/labels/{annotation_label}?api_key={settings.TEST_API_KEY}"
    )
    assert response.status_code == status.HTTP_200_OK
