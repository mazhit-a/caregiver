import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from app.application.ports import UnitOfWork
from tests.fakes.unit_of_work import FakeUnitOfWork


async def test_health_returns_200(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_unknown_route_uses_shared_error_shape(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/nope")
    assert r.status_code == 404
    error = r.json()["error"]
    assert error["code"] == "not_found"
    assert set(error) == {"code", "message", "details"}


async def test_openapi_docs_served_under_api_docs(client: httpx.AsyncClient) -> None:
    docs = await client.get("/api/docs")
    assert docs.status_code == 200
    assert "text/html" in docs.headers["content-type"]
    assert "swagger-ui" in docs.text.lower()
    spec = await client.get("/api/openapi.json")
    assert spec.status_code == 200
    assert "openapi" in spec.json()


class _Body(BaseModel):
    count: int


async def test_validation_error_uses_shared_error_shape_422(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    @app.post("/api/_probe")
    async def probe(body: _Body) -> dict[str, int]:
        return {"count": body.count}

    r = await client.post("/api/_probe", json={"count": "secret-text"})
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "validation_error"
    assert set(error) == {"code", "message", "details"}
    assert "secret-text" not in r.text


def test_fake_unit_of_work_satisfies_port() -> None:
    uow: UnitOfWork = FakeUnitOfWork()
    assert uow is not None
