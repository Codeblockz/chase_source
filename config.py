"""
Application configuration.
"""

from functools import lru_cache

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra env vars
    )

    # API Keys
    openai_api_key: str
    tavily_api_key: str

    # OpenAI Configuration
    openai_model: str = "gpt-5-mini"
    openai_temperature: float = 0.0
    openai_max_tokens: int = 2000

    # Tavily Configuration
    tavily_max_results: int = 10
    tavily_search_depth: str = "advanced"

    # Application Settings
    log_level: str = "INFO"
    gradio_server_port: int = 7860
    gradio_server_name: str = "0.0.0.0"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
