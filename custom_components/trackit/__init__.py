"""Initialisierung der Mail‑Tracker‑Integration."""
from __future__ import annotations
import logging
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Nur YAML‑Setup – keine Runtime‑Daten nötig."""
    if DOMAIN in config:
        _LOGGER.debug("Domain %s in configuration.yaml gefunden", DOMAIN)
    return True
