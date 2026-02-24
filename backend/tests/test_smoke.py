from fastapi.testclient import TestClient

from app.main import create_app



def test_application_imports_and_starts(stub_nlp_adapter_factory) -> None:
    app = create_app(nlp_adapter_factory=stub_nlp_adapter_factory)
    client = TestClient(app)

    response = client.get("/api/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
