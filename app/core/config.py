"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="WebScraperBot")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Proxy Configuration
    proxy_enabled: bool = Field(default=True)
    proxy_rotation_enabled: bool = Field(default=True)
    proxy_list: str = Field(default="")

    # Captcha Solver
    captcha_solver_enabled: bool = Field(default=True)
    captcha_solver_provider: str = Field(default="2captcha")
    twocaptcha_api_key: Optional[str] = Field(default=None)
    anticaptcha_api_key: Optional[str] = Field(default=None)

    # Browser Settings
    headless_enabled: bool = Field(default=True)
    browser_type: str = Field(default="chromium")
    browser_headless: bool = Field(default=True)
    browser_timeout: int = Field(default=30000)

    # Rate Limiting
    rate_limit_requests: int = Field(default=10)
    rate_limit_period: int = Field(default=60)

    # Request Settings
    default_timeout: int = Field(default=30)
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=1.0)
    respect_robots_txt: bool = Field(default=True)

    @property
    def proxies(self) -> List[str]:
        """Parse proxy list from comma-separated string."""
        if not self.proxy_list:
            return []
        return [p.strip() for p in self.proxy_list.split(",") if p.strip()]

    @field_validator("browser_type")
    @classmethod
    def validate_browser_type(cls, v: str) -> str:
        """Validate browser type."""
        valid_types = ["chromium", "firefox", "webkit"]
        if v.lower() not in valid_types:
            raise ValueError(f"Browser type must be one of {valid_types}")
        return v.lower()

    @field_validator("captcha_solver_provider")
    @classmethod
    def validate_captcha_provider(cls, v: str) -> str:
        """Validate captcha solver provider."""
        valid_providers = ["2captcha", "anticaptcha"]
        if v.lower() not in valid_providers:
            raise ValueError(f"Captcha provider must be one of {valid_providers}")
        return v.lower()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
