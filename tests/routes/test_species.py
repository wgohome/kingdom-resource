import pytest

#
# LOCAL FIXTURES, to be imported into conftest if to be shared with other test modules
#


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


@pytest.fixture
def two_species_in_w_duplicate(species_in_valid):
    second_species = [
        {
            "taxid": 4577,
            "name": "Zea mays",
            "alias": ["maize", "corn"],
            "cds": {
                "source": "Ensembl",
                "url": "https://www.maize.org/download/index-auto.jsp%3Fdir%3D%252Fdownload_files%252FGenes%252FTAIR10_genome_release"  # nopep8
            }
        }
    ]
    return species_in_valid + second_species


@pytest.fixture
def one_species_inserted(species_in_valid, t_client):
    # ARRANGE: ensure db has one arabidopsis
    response = t_client.post(
        "/api/v1/species",
        json=species_in_valid
    )
    assert response.status_code == 201
    return response.json()


#
# TESTS
#


def test_get_one_species(one_species_inserted, t_client):
    response = t_client.get("/api/v1/species/3702")
    assert response.status_code == 200
    assert response.json()["taxid"] == 3702


def test_get_one_species_not_found(one_species_inserted, t_client):
    response = t_client.get("/api/v1/species/101010")
    assert response.status_code == 404


def test_get_many_species_empty(t_client):
    response = t_client.get("/api/v1/species")
    assert response.status_code == 200
    assert response.json() == []


def test_get_many_species_not_empty(one_species_inserted, t_client):
    response = t_client.get("/api/v1/species")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_post_many_species_all_valid(species_in_valid, t_client):
    # Begin with empty collection
    response = t_client.post(
        "/api/v1/species",
        json=species_in_valid
    )
    assert response.status_code == 201
    assert response.json()[0]["taxid"] == species_in_valid[0]["taxid"]
    # Default values are set correctly
    assert response.json()[0]["qc_stat"]["log_processed"] == 0
    assert response.json()[0]["qc_stat"]["p_pseudoaligned"] == 0
    # Query the db to see if the item is committed
    response = t_client.get("/api/v1/species")
    assert response.json()[-1]["taxid"] == 3702


def test_any_duplicate_species_invalid(
    one_species_inserted,
    two_species_in_w_duplicate,
    t_client
):
    response = t_client.post(
        "/api/v1/species",
        json=two_species_in_w_duplicate
    )
    assert response.status_code == 409
    # Ensure that the new species is also not inserted into DB
    new_taxid = two_species_in_w_duplicate[1]["taxid"]
    response_2 = t_client.get(
        f"/api/v1/species/{new_taxid}"
    )
    assert response_2.status_code == 404


def test_duplicate_species_ignored(
    one_species_inserted,
    two_species_in_w_duplicate,
    t_client
):
    response = t_client.post(
        "/api/v1/species?skip_duplicates=true",
        json=two_species_in_w_duplicate
    )
    assert response.status_code == 201
    assert response.json()[0]["taxid"] == two_species_in_w_duplicate[1]["taxid"]
    # Check that there should be exactly two docs in collection
    response_2 = t_client.get("api/v1/species/")
    assert response_2.status_code == 200
    assert len(response_2.json()) == 2
