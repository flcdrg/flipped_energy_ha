# Flipped Energy Integration for Home Assistant

Custom Home Assistant integration for [Flipped Energy](https://flipped.energy/) account data.

This integration authenticates against the Flipped API and exposes plan, billing, and usage information as Home Assistant entities. It also imports historical usage as Recorder external statistics so you can chart it directly.

## Features

- API-only integration (no portal page parsing).
- Config flow setup with username and password.
- Sensors for:
  - plan name
  - amount due
  - usage
  - usage period end (date companion sensor)
  - total usage and total feed-in
  - import and feed-in rates (with time-of-day rate window attributes when available)
  - daily supply charge (excl and incl GST)
  - last successful update timestamp
- Binary sensors for:
  - authenticated status
  - data freshness
- Historical usage import into Home Assistant Recorder statistics (hourly and daily import usage series).

## Installation

Preferred: install with HACS

1. Open HACS in Home Assistant.
2. Go to `Integrations`.
3. Open the menu (three dots) and select `Custom repositories`.
4. Add `https://github.com/flcdrg/flipped_energy_ha` with category `Integration`.
5. Search for `Flipped Energy` in HACS and install it.
6. Restart Home Assistant.
7. Go to `Settings` -> `Devices & Services` -> `Add Integration`.
8. Search for `Flipped Energy`.
9. Enter your Flipped credentials.

Manual installation (fallback):

1. Copy `custom_components/flipped_energy` into your Home Assistant config under `custom_components`.
2. Restart Home Assistant.
3. Go to `Settings` -> `Devices & Services` -> `Add Integration`.
4. Search for `Flipped Energy`.
5. Enter your Flipped credentials.

For local development in this repository:

1. Run `scripts/setup`.
2. Run `scripts/develop`.
3. Open Home Assistant and add the integration via UI.

## Configuration Options

Available options in the integration options flow:

- refresh interval
- enable/disable plan data
- enable/disable usage data
- enable/disable invoice data

## Dashboard Cards (TOU)

Time-of-use data is exposed by these entities:

- `sensor.flipped_energy_import_tou_schedule`
- `sensor.flipped_energy_feed_in_tou_schedule`
- `sensor.flipped_energy_import_tou_blocks`
- `sensor.flipped_energy_feed_in_tou_blocks`

Ready-to-paste dashboard templates are provided in `docs/dashboard-cards.yaml`.

Important markdown rendering note:

- If you are editing a card in raw YAML mode, paste the full card block (`type`, `title`, and `content`).
- If you are editing a Markdown card's Content field in the visual editor, paste only the Jinja template body (do not include `type`, `title`, or `content`).

## Historical Statistics in Home Assistant

The integration imports historical usage into Home Assistant Recorder as external statistics.

Statistic ID pattern:

- `flipped_energy:<sanitized_entry_id>_usage_hourly_import_kwh`
- `flipped_energy:<sanitized_entry_id>_usage_daily_import_kwh`

Notes:

This project is an independent, community-built Home Assistant integration.

It is not affiliated with, endorsed by, or supported by Flipped Energy.

Flipped Energy does not provide support for this integration.

- `<sanitized_entry_id>` is based on your config entry ID and is unique per integration instance.
- Imports are incremental: each refresh only writes points newer than the latest stored timestamp.

Where to verify data:

1. Restart Home Assistant and allow at least one successful integration refresh.
2. Open Developer Tools and inspect statistics using the IDs above.

Example card (hourly):

```yaml
type: statistics-graph
entities:
  - "flipped_energy:YOUR_SANITIZED_ENTRY_ID_usage_hourly_import_kwh"
title: Flipped Hourly Import Usage
days_to_show: 2
period: hour
chart_type: bar
stat_types:
  - mean
```

Example card (daily):

```yaml
type: statistics-graph
entities:
  - "flipped_energy:YOUR_SANITIZED_ENTRY_ID_usage_daily_import_kwh"
title: Flipped Daily Import Usage
days_to_show: 30
period: day
chart_type: bar
stat_types:
  - mean
```

## Troubleshooting

- If Home Assistant UI loads in private window but not normal window, clear site data and service worker for that HA origin.
- If a stats graph card is blank:
  - ensure the `statistic_id` exactly matches Recorder metadata
  - quote IDs in YAML (because of `:`)
  - start with a minimal card and then add display options

## Development

Useful commands:

- `scripts/setup` to install dependencies
- `scripts/develop` to run Home Assistant
- `scripts/test` to run tests
- `scripts/lint` to run lint checks

Useful references:

- Integration implementation: `custom_components/flipped_energy`
- API documentation in this repo: `docs/README.md`
- Contribution guide: `CONTRIBUTING.md`

### Git pre-commit hook

Ensure Python lint (ruff) is run before each commit:

```bash
git config --local hook.lint.event pre-commit
git config --local hook.lint.command "python3 -m ruff check ."
```
