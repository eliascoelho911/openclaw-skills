from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from compras_divididas.api.app import create_app
from compras_divididas.db.models.participant import Participant
from compras_divididas.db.session import get_db_session


@pytest.fixture
def client(
    sqlite_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db_session() -> Generator[Session, None, None]:
        with sqlite_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app) as test_client:
        yield test_client


def test_list_participants_returns_two_active_participants(
    client: TestClient,
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        session.add_all(
            [
                Participant(id="ana", display_name="Ana", is_active=True),
                Participant(id="bia", display_name="Bia", is_active=True),
            ]
        )
        session.commit()

    response = client.get("/v1/participants")

    assert response.status_code == 200
    body = response.json()
    assert "participants" in body
    assert len(body["participants"]) == 2
    assert {item["id"] for item in body["participants"]} == {"ana", "bia"}


def test_openapi_contains_participants_route() -> None:
    app = create_app()
    schema = app.openapi()

    assert "/v1/participants" in schema["paths"]
    assert "get" in schema["paths"]["/v1/participants"]
