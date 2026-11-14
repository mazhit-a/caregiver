import asyncio
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
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


# --- real Postgres (docker compose up -d db): the pcn_test database is created on demand -------


async def _create_test_database(url: str) -> None:
    target = make_url(url)
    admin = create_async_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": target.database}
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    await admin.dispose()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Create the test database if missing and migrate it to head (once per run)."""
    url = Settings(_env_file=None).test_database_url  # type: ignore[call-arg]
    backend = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "alembic"))
    cfg.attributes["url"] = url
    # Own thread: the fixture may be set up while an event loop is running.
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(asyncio.run, _create_test_database(url)).result()
        pool.submit(command.upgrade, cfg, "head").result()
    return url


@pytest.fixture
async def session_factory(
    test_database_url: str,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Session factory on the migrated test database with all session data removed."""
    engine = create_async_engine(test_database_url)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE sessions, stripe_events CASCADE"))
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def db_app(
    test_database_url: str, session_factory: async_sessionmaker[AsyncSession]
) -> AsyncIterator[FastAPI]:
    """The real app wired to the test database, with a settable FixedClock in `app.state.clock`."""
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        database_url=test_database_url,
        stripe_secret_key="sk_test_dummy",
        anthropic_api_key="dummy",
    )
    app = create_app(settings)
    app.state.clock = FixedClock()
    yield app
    await app.state.engine.dispose()


@pytest.fixture
async def db_client(db_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=db_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
