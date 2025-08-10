"""Email parsing utilities for TrackIT."""
from __future__ import annotations

import re
from bs4 import BeautifulSoup
from email.message import Message
from typing import Iterable

from .models import TrackingMatch, VendorConfig


def extract_text_from_html(html: str, selectors: list[str] | None = None) -> str:
    """Extract text from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")
    if selectors:
        parts = [soup.select_one(sel) for sel in selectors]
        text = "\n".join([p.get_text(" ", strip=True) for p in parts if p])
    else:
        text = soup.get_text(" ", strip=True)
    return text


def _address_matches(address: str, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        if pattern.startswith("@") and pattern in address:
            return True
        if address == pattern:
            return True
    return False


def find_tracking_ids(text: str, patterns: Iterable[str]) -> list[str]:
    matches: list[str] = []
    for pat in patterns:
        for match in re.findall(pat, text, flags=re.IGNORECASE):
            if isinstance(match, tuple):
                match = match[0]
            matches.append(match.strip())
    return matches


def match_message(msg: Message, vendors: list[VendorConfig]) -> list[TrackingMatch]:
    """Check an email message against vendor patterns."""
    sender = msg.get("From", "")
    subject = msg.get("Subject")
    message_id = msg.get("Message-Id")
    date = msg.get("Date")
    body_text = ""
    html = None
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == "text/plain" and not body_text:
            body_text = part.get_payload(decode=True).decode(
                part.get_content_charset() or "utf-8", errors="replace"
            )
        elif ctype == "text/html" and html is None:
            html = part.get_payload(decode=True).decode(
                part.get_content_charset() or "utf-8", errors="replace"
            )

    matches: list[TrackingMatch] = []
    for vendor in vendors:
        if vendor.from_filter and not _address_matches(
            sender.lower(), [f.lower() for f in vendor.from_filter]
        ):
            continue
        text_to_search = body_text
        if vendor.html and html:
            text_to_search = extract_text_from_html(html, vendor.css_selectors or None)
        ids = find_tracking_ids(text_to_search, vendor.regex)
        for tracking_id in ids:
            snippet = _create_snippet(text_to_search, tracking_id)
            matches.append(
                TrackingMatch(
                    supplier=vendor.name,
                    tracking_id=tracking_id,
                    email_uid=0,
                    message_id=message_id,
                    subject=subject,
                    date=date,
                    sender=sender,
                    snippet=snippet,
                )
            )
    return matches


def _create_snippet(text: str, token: str, length: int = 40) -> str:
    index = text.lower().find(token.lower())
    if index == -1:
        return text[:length]
    start = max(index - length // 2, 0)
    end = min(index + len(token) + length // 2, len(text))
    return text[start:end]
