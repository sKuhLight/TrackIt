"""IMAP client for TrackIT."""
from __future__ import annotations

import email
import imaplib
import datetime as dt
from email.message import Message
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    CONF_IMAP_HOST,
    CONF_IMAP_PORT,
    CONF_SECURITY,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_MAILBOX,
)


class IMAPClient:
    """Simple asynchronous IMAP client."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        self.hass = hass
        self.config = config
        self._imap: imaplib.IMAP4 | imaplib.IMAP4_SSL | None = None

    async def async_connect(self) -> None:
        if self._imap is not None:
            return
        host = self.config[CONF_IMAP_HOST]
        port = self.config[CONF_IMAP_PORT]
        security = self.config.get(CONF_SECURITY, "SSL/TLS")

        def _connect():
            if security == "SSL/TLS":
                return imaplib.IMAP4_SSL(host, port)
            imap = imaplib.IMAP4(host, port)
            if security == "STARTTLS":
                imap.starttls()
            return imap

        self._imap = await self.hass.async_add_executor_job(_connect)
        await self.hass.async_add_executor_job(
            self._imap.login, self.config[CONF_USERNAME], self.config[CONF_PASSWORD]
        )
        await self.hass.async_add_executor_job(
            self._imap.select, self.config.get(CONF_MAILBOX, "INBOX")
        )

    async def async_search_since_uid(
        self, last_uid: int, since: dt.datetime, unseen_only: bool
    ) -> list[int]:
        await self.async_connect()
        criteria = []
        if unseen_only:
            criteria.append("UNSEEN")
        since_str = since.strftime("%d-%b-%Y")
        criteria.append(f"SINCE {since_str}")
        if last_uid:
            criteria.append(f"UID {last_uid + 1}:*")
        search_str = " ".join(criteria)

        def _search():
            assert self._imap is not None
            typ, data = self._imap.uid("SEARCH", None, search_str)
            if typ != "OK":
                return []
            ids = data[0].split()
            return [int(uid) for uid in ids]

        return await self.hass.async_add_executor_job(_search)

    async def async_fetch_message(self, uid: int) -> Message | None:
        await self.async_connect()

        def _fetch():
            assert self._imap is not None
            typ, data = self._imap.uid("FETCH", str(uid), "(RFC822)")
            if typ != "OK" or not data or data[0] is None:
                return None
            raw = data[0][1]
            return email.message_from_bytes(raw)

        return await self.hass.async_add_executor_job(_fetch)

    async def async_logout(self) -> None:
        if self._imap is None:
            return
        await self.hass.async_add_executor_job(self._imap.logout)
        self._imap = None
