#
# Hello world ping test
#


def test_main(t_client):
    response = t_client.get("/about")
    assert response.status_code == 200
