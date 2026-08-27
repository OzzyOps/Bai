"""Configuration. Fails fast and loudly on a missing secret.

A service that starts with a half-configured environment fails later, in
production, at 3am. This one refuses to start.
"""

from __future__ import annotations

from functools import lru_cache

from bai_platform.i18n import Region
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = Field(default="local")
    log_level: str = Field(default="INFO")

    # Region-scoped Supabase projects. The API only ever holds ANON keys.
    # The service-role key belongs to workers and is deliberately absent here —
    # see the boot guard below.  # service-role-guard
    supabase_urls: dict[str, str] = Field(default_factory=dict)
    supabase_anon_keys: dict[str, str] = Field(default_factory=dict)

    sentry_dsn: str | None = None
    rate_limit_per_minute: int = 120
    request_timeout_seconds: float = 30.0

    @field_validator("environment")
    @classmethod
    def known_environment(cls, v: str) -> str:
        allowed = {"local", "preview", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {sorted(allowed)}")
        return v

    def url_for(self, region: Region) -> str:
        try:
            return self.supabase_urls[region.value]
        except KeyError as exc:
            raise RuntimeError(
                f"no Supabase URL configured for region {region.value!r}. "
                f"Set SUPABASE_URLS. Customer data must never leave its region."
            ) from exc

    def anon_key_for(self, region: Region) -> str:
        try:
            return self.supabase_anon_keys[region.value]
        except KeyError as exc:
            raise RuntimeError(f"no anon key configured for region {region.value!r}") from exc


def assert_no_service_role(env: dict[str, str]) -> None:  # service-role-guard
    """The API must never hold a service-role key.

    A service-role key bypasses RLS entirely. Behind a user-facing route that is
    a total tenant-isolation failure, so we refuse to boot rather than trust
    ourselves to never use it.
    """
    leaked = [k for k in env if "SERVICE_ROLE" in k.upper() or "SERVICE_KEY" in k.upper()]  # service-role-guard
    if leaked:
        raise RuntimeError(
            f"service-role credentials present in the API environment: {leaked}. "  # service-role-guard
            f"These belong only to workers. Refusing to start."
        )


@lru_cache
def get_settings() -> Settings:
    import os

    assert_no_service_role(dict(os.environ))  # service-role-guard
    return Settings()
