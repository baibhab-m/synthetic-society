"""Centralised settings loaded from .env / process env.

Single source of truth for LLM credentials, storage, run knobs.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_api_key: str = Field(..., alias="LLM_API_KEY")
    llm_base_url: str = Field("https://api.openai.com/v1", alias="LLM_BASE_URL")
    llm_model_name: str = Field("gpt-4o-mini", alias="LLM_MODEL_NAME")
    llm_temp_extract: float = Field(0.0, alias="LLM_TEMP_EXTRACT")
    llm_temp_agent: float = Field(0.7, alias="LLM_TEMP_AGENT")
    llm_temp_report: float = Field(0.3, alias="LLM_TEMP_REPORT")

    database_url: str = Field(
        "sqlite+aiosqlite:///./synthetic_society.db", alias="DATABASE_URL"
    )

    max_agents_per_sim: int = Field(200, alias="MAX_AGENTS_PER_SIM")
    max_rounds: int = Field(20, alias="MAX_ROUNDS")
    parallel_agents: int = Field(8, alias="PARALLEL_AGENTS")

    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8765, alias="PORT")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings