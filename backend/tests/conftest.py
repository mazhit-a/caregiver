from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from app.infrastructure.config import Settings
from app.main import create_app
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        stripe_secret_key="sk_test_dummy",
        anthropic_api_key="dummy",
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
