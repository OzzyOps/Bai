"""Locale and jurisdiction resolution for BAi.

Jurisdiction is a tenant attribute, never a global constant. Nothing in the
platform may read a process-level default for region, currency or locale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

__all__ = ["REGION_ENDPOINTS", "Region", "TenantLocale"]


class Region(StrEnum):
    EU = "eu"
    UK = "uk"
    US = "us"
    APAC = "apac"
    JP = "jp"
    BR = "br"


# Physical isolation: one Supabase project and one Fly region per BAi region.
# There is no cross-region replication of customer data.
REGION_ENDPOINTS: dict[Region, dict[str, str]] = {
    Region.EU:   {"supabase_env": "SUPABASE_EU",   "fly_region": "fra", "residency": "EEA"},
    Region.UK:   {"supabase_env": "SUPABASE_UK",   "fly_region": "lhr", "residency": "GBR"},
    Region.US:   {"supabase_env": "SUPABASE_US",   "fly_region": "iad", "residency": "USA"},
    Region.APAC: {"supabase_env": "SUPABASE_APAC", "fly_region": "syd", "residency": "AUS"},
    Region.JP:   {"supabase_env": "SUPABASE_JP",   "fly_region": "nrt", "residency": "JPN"},
    Region.BR:   {"supabase_env": "SUPABASE_BR",   "fly_region": "gru", "residency": "BRA"},
}


@dataclass(frozen=True, slots=True)
class TenantLocale:
    """Resolved per request from the org record. Never defaulted globally."""

    region: Region
    locale: str                      # BCP 47, e.g. "de-DE", "ja-JP", "pt-BR"
    currency: str                    # ISO 4217 — independent of locale
    timezone: str                    # IANA, e.g. "Europe/Berlin"
    jurisdictions: tuple[str, ...] = field(default=())   # ISO 3166-1 alpha-2

    def __post_init__(self) -> None:
        if "-" not in self.locale:
            raise ValueError(f"locale must be BCP 47 with region, got {self.locale!r}")
        if len(self.currency) != 3:
            raise ValueError(f"currency must be ISO 4217 alpha-3, got {self.currency!r}")

    @property
    def residency(self) -> str:
        return REGION_ENDPOINTS[self.region]["residency"]
