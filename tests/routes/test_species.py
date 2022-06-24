from fastapi import status
import pytest

#
# LOCAL FIXTURES
# To be imported into conftest if to be shared with other test modules
#


@pytest.fixture
def one_species_list() -> list[dict]:
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
def two_species_list() -> list[dict]:
    species_list = [
        {
            "taxid": 4577,
            "name": "Zea mays",
            "alias": ["maize", "corn"],
            "cds": {
                "source": "Ensembl",
                "url": "https://www.maize.org/download/index-auto.jsp%3Fdir%3D%252Fdownload_files%252FGenes%252FTAIR10_genome_release"  # nopep8
            }
        },
        {
            "taxid": 13333,
            "name": "Amborella trichopoda",
            "cds": {
                "source": "Ensembl",
                "url": "http://ftp.ensemblgenomes.org/pub/plants/release-53/fasta/amborella_trichopoda/cds/"  # nopep8
            }
        }
    ]
    return species_list


@pytest.fixture
def two_species_list_duplicated(one_species_list) -> list[dict]:
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
    return one_species_list + second_species


@pytest.fixture
def one_species_inserted(one_species_list, t_client):
    response = t_client.post(
        "/api/v1/species",
        json=one_species_list[0]
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


#
# TESTS
#


def test_post_one_species_valid(one_species_list, t_client):
    response = t_client.post(
        "/api/v1/species",
        json=one_species_list[0]
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["taxid"] == one_species_list[0]["taxid"]


def test_post_one_species_duplicate(one_species_inserted, one_species_list, t_client):
    response = t_client.post(
        "/api/v1/species",
        json=one_species_list[0]
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_get_one_species(one_species_inserted, t_client):
    response = t_client.get("/api/v1/species/3702")
    assert response.status_code == 200
    assert response.json()["taxid"] == one_species_inserted["taxid"]


def test_get_one_species_not_found(one_species_inserted, t_client):
    response = t_client.get("/api/v1/species/101010")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_many_species_empty(t_client):
    response = t_client.get("/api/v1/species")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "page_total": 0,
        "curr_page": 1,
        "payload": []
    }


def test_get_many_species_not_empty(one_species_inserted, t_client):
    response = t_client.get("/api/v1/species")
    assert response.status_code == status.HTTP_200_OK
    res_dict = response.json()
    assert len(res_dict["payload"]) == 1
    assert res_dict["curr_page"] == 1
    assert res_dict["page_total"] == 1


# TODO: test_get_many_species_next_pages


def test_delete_one_species(one_species_inserted, t_client):
    taxid = one_species_inserted["taxid"]
    response = t_client.delete(f"/api/v1/species/{taxid}")
    assert response.status_code == status.HTTP_200_OK
    response = t_client.get(f"/api/v1/species/{taxid}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_patch_one_species(one_species_inserted, t_client):
    taxid: int = one_species_inserted["taxid"]
    to_update = {
        "name": "new species name",
        "alias": ["new species alias"],
        "cds": {
            "source": "New source",
            "url": "https://newurl.com"
        }
    }
    response = t_client.patch(
        f"/api/v1/species/{taxid}",
        json=to_update
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == to_update["name"]


# TODO: test cannot update some fields in species doc directly (via PATCH)


def test_post_many_species_all_valid(two_species_list, t_client):
    # Begin with empty collection
    response = t_client.post(
        "/api/v1/species/batch",
        json=two_species_list
    )
    assert response.status_code == 201
    assert response.json()[0]["taxid"] == two_species_list[0]["taxid"]
    # Default values are set correctly
    assert response.json()[0]["qc_stat"]["log_processed"] == 0
    assert response.json()[0]["qc_stat"]["p_pseudoaligned"] == 0
    # Query the db to see if the item is committed
    response = t_client.get("/api/v1/species")
    assert response.json()["payload"][0]["taxid"] == two_species_list[0]["taxid"]


def test_any_duplicate_species_invalid(
    one_species_inserted,
    two_species_list_duplicated,
    t_client
):
    response = t_client.post(
        "/api/v1/species/batch",
        json=two_species_list_duplicated
    )
    assert response.status_code == 409
    # Ensure that the new species is also not inserted into DB
    new_taxid = two_species_list_duplicated[1]["taxid"]
    response_2 = t_client.get(
        f"/api/v1/species/{new_taxid}"
    )
    assert response_2.status_code == 404


def test_duplicate_species_ignored(
    one_species_inserted,
    two_species_list_duplicated,
    t_client
):
    response = t_client.post(
        "/api/v1/species/batch?skip_duplicates=true",
        json=two_species_list_duplicated
    )
    assert response.status_code == 201
    assert response.json()[0]["taxid"] == two_species_list_duplicated[1]["taxid"]
    # Check that there should be exactly two docs in collection, not three
    response_2 = t_client.get("api/v1/species")
    assert response_2.status_code == 200
    assert len(response_2.json()["payload"]) == 2

# TODO: test_put_replace_species
