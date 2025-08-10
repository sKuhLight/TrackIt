"""Data models for TrackIT."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VendorConfig:
    """Configuration for a vendor."""

    name: str
    html: bool = False
    from_filter: list[str] = field(default_factory=list)
    regex: list[str] = field(default_factory=list)
    css_selectors: list[str] = field(default_factory=list)


@dataclass
class TrackingMatch:
    """Represents a tracking number found in an email."""

    supplier: str
    tracking_id: str
    email_uid: int
    message_id: str | None
    subject: str | None
    date: str | None
    sender: str | None
    snippet: str | None
    folder: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "supplier": self.supplier,
            "tracking_id": self.tracking_id,
            "subject": self.subject,
            "date": self.date,
            "from": self.sender,
            "snippet": self.snippet,
        }
