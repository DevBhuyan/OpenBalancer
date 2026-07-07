from fastapi.testclient import TestClient

from openbalancer.app import app


def test_root_redirects_to_dashboard():
    client = TestClient(app)

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard"


def test_docs_is_available():
    client = TestClient(app)

    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger" in response.text.lower()
