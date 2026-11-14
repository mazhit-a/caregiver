"""Application settings, the only place that reads the environment."""

import logging
from pathlib import Path
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_TEST_KEY_PREFIXES = ("sk_test_", "rk_test_")
# The placeholder key of .env.example: configured, but not a real Stripe account.
DUMMY_STRIPE_KEY = "sk_test_dummy"


class Settings(BaseSettings):
    """Environment-backed settings (TASK.md section 15 plus TEST_DATABASE_URL)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://pcn:pcn@localhost:55432/pcn"
    test_database_url: str = "postgresql+asyncpg://pcn:pcn@localhost:55432/pcn_test"
    anthropic_api_key: str = ""
    coach_harness: str = "single_call"
    coach_model: str = "claude-opus-5-5"
    coach_effort: str = "low"
    coach_prompt_version: str = "1"
    llm_timeout_seconds: float = 12
    eval_judge_model: str = "claude-opus-5-5"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    public_app_url: str = "http://localhost:3000"
    cors_origins: str = ""
    content_dir: Path = Path(__file__).resolve().parents[3] / "content"
    demo_controls: bool = True
    roleplay_turns_per_hour: int = 40
    public_card_requests_per_minute: int = 30

    @model_validator(mode="after")
    def _validate(self) -> Self:
        key = self.stripe_secret_key
        if key and not key.startswith(_TEST_KEY_PREFIXES):
            raise ValueError("STRIPE_SECRET_KEY must be a test key (sk_test_ or rk_test_)")
        if not self.anthropic_api_key:
            logger.warning("ANTHROPIC_API_KEY is empty: role-play will use the fallback only")
        return self

    @property
    def stripe_enabled(self) -> bool:
        """Stripe is on when a key is configured that is not the `.env.example` dummy."""
        return bool(self.stripe_secret_key) and self.stripe_secret_key != DUMMY_STRIPE_KEY

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
