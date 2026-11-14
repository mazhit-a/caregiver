import shutil
from pathlib import Path

import pytest

from app.infrastructure.config import Settings
from app.infrastructure.content.loader import ContentLoadError
from app.main import create_app

REAL_CONTENT = Path(__file__).resolve().parents[3] / "content"


def _settings(content_dir: Path) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        anthropic_api_key="dummy",
        content_dir=content_dir,
    )


async def test_lifespan_loads_content_into_app_state() -> None:
    app = create_app(_settings(REAL_CONTENT))
    async with app.router.lifespan_context(app):
        assert app.state.content.content_version
        assert "m1_l1" in app.state.content.lesson_ids()


async def test_app_refuses_to_start_on_invalid_content(tmp_path: Path) -> None:
    broken = tmp_path / "content"
    shutil.copytree(REAL_CONTENT, broken)
    (broken / "quiz.json").write_text('{"version": 3}')
    app = create_app(_settings(broken))
    with pytest.raises(ContentLoadError, match=r"quiz\.json: .*(required|Field)"):
        async with app.router.lifespan_context(app):
            pass


async def test_app_refuses_to_start_when_content_dir_is_missing(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path / "nowhere"))
    with pytest.raises(ContentLoadError, match="content directory not found"):
        async with app.router.lifespan_context(app):
            pass
