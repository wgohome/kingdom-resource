import math
from fastapi import status
import pytest

from config import settings

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
def twenty_one_species_list() -> list[dict]:
    species_list = [
        {
            "taxid": 9000 + i,
            "name": f"Species name for {9000 + i}",
            "alias": [f"alias {i}"],
            "cds": {
                "source": "Ensembl",
                "url": f"https://www.cds.net/spp/{9000 + i}"
            }
        }
        for i in range(1, 22)
    ]
    return species_list


@pytest.fixture
def one_species_inserted(one_species_list, t_client):
    response = t_client.post(
        "/api/v1/species",
        json=one_species_list[0]
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def twenty_one_species_inserted(twenty_one_species_list, t_client):
    response = t_client.post(
        "/api/v1/species/batch",
        json=twenty_one_species_list
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


def test_get_many_species_w_pages(twenty_one_species_inserted, t_client):
    # Test second page full
    response = t_client.get("/api/v1/species?page_num=2")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["payload"]) == settings.PAGE_SIZE
    # Test page total correct
    last_page = response.json()["page_total"]
    assert last_page == math.ceil(len(twenty_one_species_inserted) / settings.PAGE_SIZE)
    # TODO Test page negative error
    # Test last page one doc only
    response = t_client.get(f"/api/v1/species?page_num={last_page}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["payload"]) != 0
    # Test fourth page empty
    response = t_client.get(f"/api/v1/species?page_num={last_page + 1}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["payload"]) == 0


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


def test_patch_one_species_unauthorized_field(one_species_inserted, t_client):
    # Cannot update some restricted fields in species doc directly (via PATCH)
    taxid: int = one_species_inserted["taxid"]
    to_update = {
        "name": "new species name",
        "alias": ["new species alias"],
        "cds": {
            "source": "New source",
            "url": "https://newurl.com"
        },
        "qc_stat": {
            "log_processed": 1,
            "p_pseudoaligned": 2
        }
    }
    response = t_client.patch(
        f"/api/v1/species/{taxid}",
        json=to_update
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_post_many_species_all_valid(two_species_list, t_client):
    # Begin with empty collection
    response = t_client.post(
        "/api/v1/species/batch",
        json=two_species_list
    )
    assert response.status_code == status.HTTP_201_CREATED
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
    assert response.status_code == status.HTTP_409_CONFLICT
    # Ensure that the none of the new species is also not inserted into DB
    new_taxid = two_species_list_duplicated[1]["taxid"]
    response_2 = t_client.get(
        f"/api/v1/species/{new_taxid}"
    )
    assert response_2.status_code == status.HTTP_404_NOT_FOUND


def test_duplicate_species_ignored(
    one_species_inserted,
    two_species_list_duplicated,
    t_client
):
    response = t_client.post(
        "/api/v1/species/batch?skip_duplicates=true",
        json=two_species_list_duplicated
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()[0]["taxid"] == two_species_list_duplicated[1]["taxid"]
    # Check that there should be exactly two docs in collection, not three
    response_2 = t_client.get("api/v1/species")
    assert response_2.status_code == status.HTTP_200_OK
    assert len(response_2.json()["payload"]) == 2


def test_put_replace_species(twenty_one_species_inserted, one_species_list, t_client):
    # Replaces existing document -> for fields not defined in update,
    #   even if old doc has the field, will be replaced by default values set
    #
    to_replace = twenty_one_species_inserted[0]
    to_replace["name"] = to_replace["name"] + "_modified"
    to_replace.pop("_id")
    to_replace.pop("qc_stat")
    to_replace.pop("created_at")
    to_replace.pop("updated_at")
    response = t_client.put(
        "/api/v1/species/batch",
        json=one_species_list + [to_replace]
    )
    assert response.status_code == status.HTTP_200_OK
    response = t_client.get(f"/api/v1/species/{to_replace['taxid']}")
    assert response.status_code == status.HTTP_200_OK
    assert "modified" in response.json()["name"]
    assert response.json()["qc_stat"] == {"log_processed": 0, "p_pseudoaligned": 0}
