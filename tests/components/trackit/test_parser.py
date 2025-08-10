from email.message import EmailMessage

from custom_components.trackit.parser import match_message
from custom_components.trackit.models import VendorConfig


def test_match_message_plain_text():
    msg = EmailMessage()
    msg["From"] = "noreply@dhl.de"
    msg.set_content("Your tracking JJD1234567890123 is ready")
    vendor = VendorConfig(
        name="DHL",
        html=False,
        from_filter=["@dhl.de"],
        regex=[r"JJD\d+"],
    )
    matches = match_message(msg, [vendor])
    assert matches
    assert matches[0].tracking_id == "JJD1234567890123"
