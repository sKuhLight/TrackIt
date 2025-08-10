import pytest
from types import SimpleNamespace

from custom_components.trackit.const import CONF_VENDORS
from custom_components.trackit.models import VendorConfig
from custom_components.trackit.store import TrackItStore


class FakeStore:
    def __init__(self, hass, version, key):
        self.data = {"last_uid": 0, "vendors": [], "cache": []}
        self.saved = None

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.saved = data
        self.data = data


@pytest.mark.asyncio
async def test_async_load_updates_vendors_from_options(monkeypatch):
    """Ensure options vendors are stored and loaded."""
    monkeypatch.setattr("custom_components.trackit.store.Store", FakeStore)
    vendor = VendorConfig(name="DHL", regex=["\\d+"])
    entry = SimpleNamespace(entry_id="1", options={CONF_VENDORS: [vars(vendor)]})
    store = TrackItStore(None, entry)
    await store.async_load()
    assert store.vendors == [vendor]
    assert store._store.saved["vendors"] == [vars(vendor)]
