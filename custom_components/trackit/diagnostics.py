"""Diagnostics support for TrackIT."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, CONF_PASSWORD, CONF_USERNAME


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    data = {
        k: v for k, v in entry.data.items() if k not in {CONF_PASSWORD, CONF_USERNAME}
    }
    return {
        "entry": data,
        "options": entry.options,
        "last_uid": hass.data[DOMAIN][entry.entry_id]["store"].last_uid,
    }
