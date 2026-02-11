from fastapi import FastAPI
from fastapi.testclient import TestClient

from compras_divididas.api.error_handlers import register_error_handlers
from compras_divididas.domain.errors import DuplicateExternalIDError


def test_domain_error_handler_returns_contract_shape() -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise DuplicateExternalIDError(message="Duplicated movement")

    client = TestClient(app)
    response = client.get("/boom")

    assert response.status_code == 409
    assert response.json() == {
        "code": "DUPLICATE_EXTERNAL_ID",
        "message": "Duplicated movement",
    }
