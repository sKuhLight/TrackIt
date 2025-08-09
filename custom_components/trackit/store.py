"""Storage helper for TrackIT."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION, CONF_VENDORS
from .models import VendorConfig, TrackingMatch


class TrackItStore:
    """Handle persistent storage for TrackIT."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self.data: dict = {}
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.json")

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if data is None:
            data = {
                "last_uid": 0,
                "vendors": self.entry.options.get(CONF_VENDORS, []),
                "cache": [],
            }
        self.data = data

    async def async_save(self) -> None:
        await self._store.async_save(self.data)

    @property
    def last_uid(self) -> int:
        return self.data.get("last_uid", 0)

    def set_last_uid(self, uid: int) -> None:
        self.data["last_uid"] = uid

    @property
    def vendors(self) -> list[VendorConfig]:
        return [VendorConfig(**v) for v in self.data.get("vendors", [])]

    def set_vendors(self, vendors: list[VendorConfig]) -> None:
        self.data["vendors"] = [vars(v) for v in vendors]

    @property
    def cache(self) -> list[dict]:
        return self.data.get("cache", [])

    def update_cache(self, matches: list[TrackingMatch], max_matches: int) -> None:
        cache = [m.as_dict() for m in matches] + self.cache
        self.data["cache"] = cache[:max_matches]
