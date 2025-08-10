# TrackIT Home Assistant Integration

TrackIT is a custom Home Assistant integration that scans an IMAP mailbox for tracking numbers and exposes them as a single sensor.

## Installation

1. Copy the `custom_components/trackit` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & services → Add Integration** and search for **TrackIT**.

## Configuration

All configuration is handled in the UI. Provide your IMAP credentials and adjust options such as scan interval and vendors. A sample DHL vendor can be added from the options flow.

## Testing

Run tests and linters:

```bash
pip install -r requirements_test.txt  # if needed
pre-commit run --files <changed files>
pytest
```

## Screenshots

*(Add screenshots of config flow and sensor here)*

## Troubleshooting

Check the Home Assistant logs for messages from `homeassistant.components.trackit`.
