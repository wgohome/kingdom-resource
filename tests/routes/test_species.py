import pytest


@pytest.fixture
def species_in_valid():
    return [
        {
            "taxid": 3702,
            "name": "Arabidopsis thaliana",
            "alias": ["thale cress"],
            "cds": {
                "source": "TAIR10",
                "url": "https://www.arabidopsis.org/download/index-auto.jsp%3Fdir%3D%252Fdownload_files%252FGenes%252FTAIR10_genome_release"  # nopep8
            }
        }
    ]


def test_get_many_species_empty(t_client):
    response = t_client.get(
        "/api/v1/species"
    )
    assert response.status_code == 200
    assert response.json() == []


def test_post_many_species_valid(species_in_valid, t_client):
    response = t_client.post(
        "/api/v1/species",
        json=species_in_valid
    )
    assert response.status_code == 201
    assert response.json()[0]["taxid"] == 3702
    assert response.json()[0]["qc_stat"]["log_processed"] == 0
    assert response.json()[0]["qc_stat"]["p_pseudoaligned"] == 0
    # TODO: Query the db to see if the item is there


def test_get_one_species(species_in_valid, t_client):
    pass
