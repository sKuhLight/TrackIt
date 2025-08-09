"""Coordinator for TrackIT."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_SCAN_WINDOW_DAYS,
    CONF_UNSEEN_ONLY,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    CONF_MAX_MATCHES,
    DEFAULT_MAX_MATCHES,
    LOGGER_NAME,
)
from .imap_client import IMAPClient
from .parser import match_message
from .store import TrackItStore
from .models import TrackingMatch


class TrackItCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator to manage updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry,
        imap_client: IMAPClient,
        store: TrackItStore,
    ) -> None:
        self.config_entry = config_entry
        self.imap_client = imap_client
        self.store = store
        interval = timedelta(
            minutes=config_entry.options.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES
            )
        )
        self.logger = logging.getLogger(LOGGER_NAME)
        super().__init__(
            hass,
            self.logger,
            name="TrackIT Coordinator",
            update_interval=interval,
        )

    async def _async_update_data(self) -> list[dict[str, Any]]:
        last_uid = self.store.last_uid
        window = self.config_entry.data.get(CONF_SCAN_WINDOW_DAYS, 14)
        unseen_only = self.config_entry.data.get(CONF_UNSEEN_ONLY, True)
        since = datetime.now() - timedelta(days=window)

        try:
            uids = await self.imap_client.async_search_since_uid(
                last_uid, since, unseen_only
            )
        except Exception as err:  # pragma: no cover - imap errors
            raise UpdateFailed(str(err)) from err

        new_matches: list[TrackingMatch] = []
        max_uid = last_uid
        vendors = self.store.vendors
        for uid in uids:
            msg = await self.imap_client.async_fetch_message(uid)
            if not msg:
                continue
            for match in match_message(msg, vendors):
                match.email_uid = uid
                new_matches.append(match)
            if uid > max_uid:
                max_uid = uid
        if max_uid != last_uid:
            self.store.set_last_uid(max_uid)

        max_matches = self.config_entry.options.get(
            CONF_MAX_MATCHES, DEFAULT_MAX_MATCHES
        )
        self.store.update_cache(new_matches, max_matches)
        await self.store.async_save()
        return self.store.cache
