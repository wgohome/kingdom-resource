import json
import math
import pytest
from fastapi import status

from config import settings

#
# FIXTURES
#


@pytest.fixture
def genes_1(many_genes_inserted):
    genes, taxid = many_genes_inserted
    labels = [gene["label"] for gene in genes]
    return labels[::2], taxid


@pytest.fixture
def genes_2(many_genes_inserted):
    genes, taxid = many_genes_inserted
    labels = [gene["label"] for gene in genes]
    return labels[::3], taxid


@pytest.fixture
def ga_dict_1(genes_1):
    genes = [
        {
            "taxid": genes_1[1],
            "gene_label": gene_label
        }
        for gene_label in genes_1[0]
    ]
    ga_dict = {
        "type": "test_mercator",
        "label": "1.1.1.2.2.1",
        "details": {
            "desc": "component PsbO/OEC33 of PS-II oxygen-evolving center",
            "binname": "Photosynthesis.photophosphorylation.photosystem II.PS-II complex.oxygen-evolving center (OEC) extrinsic proteins.component OEC33/PsbO"
        },
        "genes": genes
    }
    return ga_dict


@pytest.fixture
def ga_dict_2(genes_2):
    genes = [
        {
            "taxid": genes_2[1],
            "gene_label": gene_label
        }
        for gene_label in genes_2[0]
    ]
    ga_dict = {
        "type": "test_mercator",
        "label": "1.1.1.2.1.1",
        "details": {
            "desc": "component PsbA/D1 of PS-II reaction center complex",
            "binname": "Photosynthesis.photophosphorylation.photosystem II.PS-II complex.reaction center complex.component D1/PsbA"
        },
        "genes": genes
    }
    return ga_dict


@pytest.fixture
def twenty_one_gas_list(many_genes_inserted):
    genes, taxid = many_genes_inserted
    return [
        {
            "type": f"Gene Annotation Type {i // 5 + 1}",
            "label": f"Gene Annotation Label {i}",
            "details": {
                "description": f"rubbish {i}"
            },
            "genes": [
                {
                    "taxid": taxid,
                    "gene_label": gene["label"]
                }
                for gene in genes[:len(genes) - 1]
            ]
        }
        for i in range(1, 22)
    ]


@pytest.fixture
def ga_dict_1_inserted(ga_dict_1, t_client):
    response = t_client.post(
        "/api/v1/gene_annotations",
        json=ga_dict_1
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def twenty_one_gas_inserted(twenty_one_gas_list, t_client):
    response = t_client.post(
        "/api/v1/gene_annotations/batch",
        json=twenty_one_gas_list
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


#
# TESTS
#


def test_post_one_ga_valid(ga_dict_1_inserted, ga_dict_1, t_client):
    ga = ga_dict_1_inserted
    assert ga["type"] == ga_dict_1["type"]
    assert ga["label"] == ga_dict_1["label"]
    assert len(ga["gene_ids"]) == len(ga_dict_1["genes"])


def test_post_one_ga_duplicate(ga_dict_1_inserted, ga_dict_1, t_client):
    response = t_client.post(
        "/api/v1/gene_annotations",
        json=ga_dict_1
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_get_one_ga(ga_dict_1_inserted, t_client):
    type = ga_dict_1_inserted["type"]
    label = ga_dict_1_inserted["label"]
    response = t_client.get(f"/api/v1/gene_annotations/type/{type}/label/{label}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["type"] == type
    assert response.json()["label"] == label


def test_get_one_ga_not_found(ga_dict_1_inserted, t_client):
    response = t_client.get("/api/v1/gene_annotations/type/dummy/label/X123")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_many_gas_empty(t_client):
    response = t_client.get("/api/v1/gene_annotations")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "page_total": 0,
        "curr_page": 1,
        "payload": []
    }


def test_get_many_gas_not_empty(twenty_one_gas_inserted, t_client):
    response = t_client.get("/api/v1/gene_annotations")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["curr_page"] == 1
    assert response.json()["page_total"] == math.ceil(len(twenty_one_gas_inserted) / settings.PAGE_SIZE)
    payload = response.json()["payload"]
    assert len(payload) == settings.PAGE_SIZE
    # Check data format
    ga_dict = twenty_one_gas_inserted[0]
    assert payload[0]["type"] == ga_dict["type"]
    assert payload[0]["label"] == ga_dict["label"]


def test_get_many_gas_w_pages(twenty_one_gas_inserted, t_client):
    gas = twenty_one_gas_inserted
    # Test second page full
    response = t_client.get("/api/v1/gene_annotations?page_num=2")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["payload"]) == settings.PAGE_SIZE
    # Test page total correct
    last_page = response.json()["page_total"]
    assert last_page == math.ceil(len(gas) / settings.PAGE_SIZE)
    # TODO Test page negative error
    # Test last page one doc only
    response = t_client.get(f"/api/v1/gene_annotations?page_num={last_page}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["payload"]) != 0
    # Test fourth page empty
    response = t_client.get(f"/api/v1/gene_annotations?page_num={last_page + 1}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["payload"]) == 0


# TODO get many gas filter by type and/or labels


def test_delete_one_ga(ga_dict_1_inserted, t_client):
    ga_type, label = ga_dict_1_inserted["type"], ga_dict_1_inserted["label"]
    response = t_client.delete(f"/api/v1/gene_annotations/type/{ga_type}/label/{label}")
    assert response.status_code == status.HTTP_200_OK
    response = t_client.get(f"/api/v1/gene_annotations/type/{ga_type}/label/{label}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_patch_one_ga(ga_dict_1_inserted, t_client):
    ga_type = ga_dict_1_inserted["type"]
    label = ga_dict_1_inserted["label"]
    to_update = {
        "type": "new type name",
        "label": "new label name",
        "details": {"content": "no more details!"}
    }
    response = t_client.patch(
        f"/api/v1/gene_annotations/type/{ga_type}/label/{label}",
        json=to_update
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["label"] == to_update["label"]


def test_patch_one_ga_unauthorized_field(ga_dict_1_inserted, t_client):
    ga_type = ga_dict_1_inserted["type"]
    label = ga_dict_1_inserted["label"]
    to_update = {
        "type": "new type name",
        "label": "new label name",
        "details": {"content": "no more details!"},
        "genes_ids": ["123456789012345678901234"]
    }
    response = t_client.patch(
        f"/api/v1/gene_annotations/type/{ga_type}/label/{label}",
        json=to_update
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_post_many_gas_all_valid(twenty_one_gas_inserted, twenty_one_gas_list):
    res_data = twenty_one_gas_inserted
    in_data = twenty_one_gas_list
    assert len(res_data) == len(in_data)
    assert {ga["type"] for ga in res_data} == {ga["type"] for ga in in_data}
    assert {ga["label"] for ga in res_data} == {ga["label"] for ga in in_data}
    for i in range(0, len(res_data), 7):
        assert len(res_data[i]["gene_ids"]) > 0
        assert len(res_data[i]["gene_ids"]) == len(in_data[i]["genes"])


def test_any_duplicate_gas_invalid(
    ga_dict_1_inserted,
    ga_dict_1,
    ga_dict_2,
    t_client
):
    response = t_client.post(
        "/api/v1/gene_annotations/batch",
        json=[ga_dict_1, ga_dict_2]
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_duplicate_gas_ignored(
    ga_dict_1_inserted,
    ga_dict_1,
    ga_dict_2,
    t_client
):
    response = t_client.post(
        "/api/v1/gene_annotations/batch?skip_duplicates=true",
        json=[ga_dict_1, ga_dict_2]
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert len(response.json()) == 1


def test_put_replace_gas(twenty_one_gas_inserted, ga_dict_1, t_client):
    # Replaces existing document -> for fields not defined in update,
    #   even if old doc has the field, will be replaced by default values set
    #
    to_replace = twenty_one_gas_inserted[0]
    to_replace["label"] = to_replace["label"] + "_modified"
    to_replace["genes"] = []  # TODO
    to_replace.pop("_id")
    to_replace.pop("gene_ids")
    response = t_client.put(
        "/api/v1/gene_annotations/batch",
        json=[ga_dict_1, to_replace]
    )
    assert response.status_code == status.HTTP_200_OK
    ga_type = to_replace["type"]
    label = to_replace["label"]
    response = t_client.get(f"/api/v1/gene_annotations/type/{ga_type}/label/{label}")
    assert response.status_code == status.HTTP_200_OK
    # TODO better check that old doc completely replaced, perhaps check gene ids replace by new ones?


#
# Batch update to append gene_ids to GeneAnnotationDoc if present
# otherwise, create new Doc
#
def test_patch_gas_batch(
    twenty_one_gas_inserted,
    twenty_one_gas_list,
    ga_dict_2,
    t_client
):
    ga_1_original = twenty_one_gas_list[0]
    # NOTE: this deepcopy implementation only works if json is serializable,
    #   eg, in this case no ObjectId in the dict yet
    ga_1_modified = json.loads(json.dumps(ga_1_original))
    ga_1_modified["genes"] = [ga_dict_2["genes"][-1]]
    ga_1_modified["details"]["desc"] = "new description"
    response = t_client.patch(
        "/api/v1/gene_annotations/batch",
        json=[ga_dict_2, ga_1_modified]
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2
    # Check that ga dict 2 is created
    response = t_client.get(f"/api/v1/gene_annotations/type/{ga_dict_2['type']}/label/{ga_dict_2['label']}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["type"] == ga_dict_2["type"]
    assert response.json()["label"] == ga_dict_2["label"]
    # Check that one gene is added to existing ga_1 doc in the db
    response = t_client.get(f"/api/v1/gene_annotations/type/{ga_1_modified['type']}/label/{ga_1_modified['label']}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["gene_ids"]) > len(ga_1_original["genes"])
    assert response.json()["details"] == ga_1_original["details"]
