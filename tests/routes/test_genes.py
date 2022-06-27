import math
import pytest
from fastapi import status

from config import settings

#
# LOCAL FIXTURES
#


@pytest.fixture
def one_gene() -> dict:
    return {
        "label": "H001",
        "alias": ["gene h001"]
    }


@pytest.fixture
def genes_in_valid(one_species_inserted):
    species_taxid = one_species_inserted['taxid']
    genes = []
    for i in range(1, 11):
        genes.append({"label": f"G00{i}", "alias": [f"alias for gene {i}"]})
    return genes, species_taxid


@pytest.fixture
def genes_in_some_repetition(one_species_inserted):
    species_taxid = one_species_inserted['taxid']
    genes = []
    for i in range(11, 21):
        genes.append({
            "label": f"G00{i}",
            "alias": [f"alias for gene {i}"]
        })
    genes.append({
        "label": "G001",
        "alias": ["alias for gene 1"]
    })
    return genes, species_taxid


@pytest.fixture
def twenty_one_genes_list(one_species_inserted):
    species_taxid = one_species_inserted['taxid']
    species_list = [
        {
            "label": f"Gene{8000 + i}",
            "alias": [f"alias gene {8000 + i} spp {species_taxid}"]
        }
        for i in range(1, 22)
    ]
    return species_list, species_taxid


@pytest.fixture
def one_gene_inserted(one_species_inserted, one_gene, t_client):
    taxid = one_species_inserted['taxid']
    response = t_client.post(
        f"/api/v1/species/{taxid}/genes",
        json=one_gene
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json(), taxid


@pytest.fixture
def many_genes_inserted(genes_in_valid, t_client):
    genes, taxid = genes_in_valid
    response = t_client.post(
        f"/api/v1/species/{taxid}/genes/batch",
        json=genes
    )
    assert response.status_code == 201
    return response.json(), taxid


@pytest.fixture
def twenty_one_genes_inserted(twenty_one_genes_list, t_client):
    genes, taxid = twenty_one_genes_list
    response = t_client.post(
        f"/api/v1/species/{taxid}/genes/batch",
        json=genes
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json(), taxid


#
# TESTS
#


def test_post_one_gene_valid(one_gene_inserted, one_gene):
    gene, _ = one_gene_inserted
    assert gene["label"] == one_gene["label"]


def test_post_one_gene_duplicate(one_gene_inserted, one_gene, t_client):
    _, taxid = one_gene_inserted
    response = t_client.post(
        f"/api/v1/species/{taxid}/genes",
        json=one_gene
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_get_one_gene(one_gene_inserted, t_client):
    gene, taxid = one_gene_inserted
    response = t_client.get(f"/api/v1/species/{taxid}/genes/{gene['label']}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["label"] == gene["label"]


def test_get_one_gene_not_found(one_gene_inserted, t_client):
    _, taxid = one_gene_inserted
    response = t_client.get(f"/api/v1/species/{taxid}/genes/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_many_genes_empty(one_species_inserted, t_client):
    taxid = one_species_inserted['taxid']
    response = t_client.get(f"/api/v1/species/{taxid}/genes")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "page_total": 0,
        "curr_page": 1,
        "payload": []
    }


def test_get_many_genes_not_empty(many_genes_inserted, t_client):
    genes, taxid = many_genes_inserted
    response = t_client.get(f"/api/v1/species/{taxid}/genes")
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()["payload"]
    assert len(payload) == len(genes)
    # Ensure only taxid 3702 returned
    species_id_list = list(set([doc['species_id'] for doc in payload]))
    assert len(species_id_list) == 1
    response_2 = t_client.get(f"/api/v1/species/{taxid}")
    assert species_id_list[0] == response_2.json()['_id']


def test_get_many_genes_w_pages(twenty_one_genes_inserted, t_client):
    genes, taxid = twenty_one_genes_inserted
    # Test second page full
    response = t_client.get(f"/api/v1/species/{taxid}/genes?page_num=2")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["payload"]) == settings.PAGE_SIZE
    # Test page total correct
    last_page = response.json()["page_total"]
    assert last_page == math.ceil(len(genes) / settings.PAGE_SIZE)
    # TODO Test page negative error
    # Test last page one doc only
    response = t_client.get(f"/api/v1/species/{taxid}/genes?page_num={last_page}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["payload"]) != 0
    # Test fourth page empty
    response = t_client.get(f"/api/v1/species/{taxid}/genes?page_num={last_page + 1}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["payload"]) == 0


def test_delete_one_gene(one_gene_inserted, t_client):
    gene, taxid = one_gene_inserted
    response = t_client.delete(f"/api/v1/species/{taxid}/genes/{gene['label']}")
    assert response.status_code == status.HTTP_200_OK
    response = t_client.get(f"/api/v1/species/{taxid}/genes/{gene['label']}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_patch_one_gene(one_gene_inserted, t_client):
    gene, taxid = one_gene_inserted
    to_update = {
        "label": "new gene name",
        "alias": ["new gene alias"]
    }
    response = t_client.patch(
        f"/api/v1/species/{taxid}/genes/{gene['label']}",
        json=to_update
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["label"] == to_update["label"]


def test_patch_one_gene_unauthorized_field(one_gene_inserted, t_client):
    # Cannot update some restricted fields in species doc directly (via PATCH)
    gene, taxid = one_gene_inserted
    to_update = {
        "label": "new gene name",
        "alias": ["new gene alias"],
        "anots": ["123456789012345678901234"]
    }
    response = t_client.patch(
        f"/api/v1/species/{taxid}/genes/{gene['label']}",
        json=to_update
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_post_many_genes_all_valid(genes_in_valid, many_genes_inserted):
    genes, _ = genes_in_valid
    res_data, _ = many_genes_inserted
    assert len(genes) == len(res_data)
    res_subset = [
        {k: v for k, v in gene.items() if k in ["label", "alias"]}
        for gene in res_data
    ]
    assert genes == res_subset


def test_any_duplicate_gene_invalid(
    many_genes_inserted,
    genes_in_some_repetition,
    t_client
):
    genes, _ = genes_in_some_repetition
    response = t_client.post(
        "/api/v1/species/3702/genes/batch",
        json=genes
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_duplicate_genes_ignored(
    many_genes_inserted,
    genes_in_some_repetition,
    t_client
):
    genes, _ = genes_in_some_repetition
    response = t_client.post(
        "/api/v1/species/3702/genes/batch?skip_duplicates=true",
        json=genes
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert len(response.json()) < len(genes_in_some_repetition[0])


def test_put_replace_genes(twenty_one_genes_inserted, one_gene, t_client):
    # Replaces existing document -> for fields not defined in update,
    #   even if old doc has the field, will be replaced by default values set
    #
    genes, taxid = twenty_one_genes_inserted
    to_replace = genes[0]
    to_replace["label"] = to_replace["label"] + "_modified"
    to_replace.pop("_id")
    to_replace.pop("species_id")
    to_replace.pop("annotations")
    response = t_client.put(
        f"/api/v1/species/{taxid}/genes/batch",
        json=[one_gene, to_replace]
    )
    assert response.status_code == status.HTTP_200_OK
    response = t_client.get(f"/api/v1/species/{taxid}/genes/{to_replace['label']}")
    assert response.status_code == status.HTTP_200_OK
    assert "modified" in response.json()["label"]
