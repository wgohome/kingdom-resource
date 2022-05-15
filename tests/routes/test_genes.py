import pytest
from fastapi import status

#
# LOCAL FIXTURES
#


@pytest.fixture
def genes_in_valid(one_species_inserted):
    species_taxid = one_species_inserted[0]['taxid']
    genes = []
    for i in range(1, 11):
        genes.append({
            "label": f"G00{i}",
            "name": f"Gene {i}",
            "description": f"This is Gene {i}"
        })
    return genes, species_taxid


@pytest.fixture
def genes_in_some_repetition(one_species_inserted):
    species_taxid = one_species_inserted[0]['taxid']
    genes = []
    for i in range(11, 21):
        genes.append({
            "label": f"G00{i}",
            "name": f"Gene {i}",
            "description": f"This is Gene {i}",
        })
    genes.append({
        "label": "G001",
        "name": "Gene 1",
        "description": "This is Gene 1",
    })
    return genes, species_taxid


@pytest.fixture
def many_genes_inserted(genes_in_valid, t_client):
    genes, species_taxid = genes_in_valid
    response = t_client.post(
        f"/api/v1/species/{species_taxid}/genes",
        json=genes
    )
    assert response.status_code == 201
    return response.json()


#
# TESTS
#


def test_get_genes_empty(one_species_inserted, t_client):
    response = t_client.get("/api/v1/species/3702/genes")
    assert response.status_code == 200
    assert response.json() == []


def test_get_genes_not_empty(many_genes_inserted, t_client):
    response = t_client.get("/api/v1/species/3702/genes")
    assert response.status_code == 200
    assert len(response.json()) == len(many_genes_inserted)
    # Ensure only taxid 3702 returned
    species_id_list = list(set([doc['species_id'] for doc in response.json()]))
    assert len(species_id_list) == 1
    response_2 = t_client.get("/api/v1/species/3702")
    assert species_id_list[0] == response_2.json()['_id']


def test_post_many_genes_all_valid(genes_in_valid, many_genes_inserted, t_client):
    genes, _ = genes_in_valid
    res_data = many_genes_inserted
    assert len(genes) == len(res_data)
    res_subset = [
        {k: v for k, v in gene.items() if k in ["label", "name", "description"]}
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
        "/api/v1/species/3702/genes",
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
        "/api/v1/species/3702/genes?skip_duplicates=true",
        json=genes
    )
    assert response.status_code == status.HTTP_201_CREATED
