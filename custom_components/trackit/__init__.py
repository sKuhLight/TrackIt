"""TrackIT integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, SERVICE_RESCAN
from .coordinator import TrackItCoordinator
from .store import TrackItStore
from .imap_client import IMAPClient

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TrackIT from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    store = TrackItStore(hass, entry)
    await store.async_load()

    imap_client = IMAPClient(hass, entry.data)
    coordinator = TrackItCoordinator(
        hass,
        config_entry=entry,
        imap_client=imap_client,
        store=store,
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "store": store,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Schedule the first refresh in the background so config entry setup doesn't
    # block for large initial scans. Sensor state will update once the refresh
    # completes.
    hass.async_create_background_task(
        coordinator.async_config_entry_first_refresh(),
        f"{DOMAIN}_first_refresh_{entry.entry_id}",
    )

    async def _handle_rescan(call) -> None:
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_RESCAN, _handle_rescan)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["coordinator"].imap_client.async_logout()
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_RESCAN)
    return unload_ok
