# Agent Instructions For flipped_energy_ha

This file helps AI coding agents become productive quickly in this repository.

## Scope

- Home Assistant custom integration code lives in [custom_components/flipped_energy](custom_components/flipped_energy).
- Runtime Home Assistant config for local development lives in [config](config).
- Tests live in [tests](tests).

## Fast Start Commands

- Install dependencies: run scripts/setup
- Start Home Assistant dev instance: run scripts/develop
- Run lint and auto-fixes: run scripts/lint
- Run tests: run scripts/test

## Workflow Expectations

- Before coding, read [README.md](README.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
- Prefer minimal edits and keep changes scoped to the user request.
- Validate with scripts/test for behavior changes and scripts/lint for style changes.

## Architecture Notes

- Entry setup and platform forwarding: [custom_components/flipped_energy/__init__.py](custom_components/flipped_energy/__init__.py)
- API client and typed API errors: [custom_components/flipped_energy/api.py](custom_components/flipped_energy/api.py)
- Coordinator polling and error mapping: [custom_components/flipped_energy/coordinator.py](custom_components/flipped_energy/coordinator.py)
- Config flow: [custom_components/flipped_energy/config_flow.py](custom_components/flipped_energy/config_flow.py)
- Domain constants: [custom_components/flipped_energy/const.py](custom_components/flipped_energy/const.py)

## Project Conventions

- Use async-first Home Assistant patterns and typed exceptions in the API layer.
- Keep imports and typing style consistent with existing files.
- Keep tests aligned with pytest-homeassistant-custom-component fixtures in [tests/conftest.py](tests/conftest.py).

## Known Pitfalls

- scripts/develop bootstraps dependencies if Home Assistant modules are missing; prefer running scripts/develop from repo root.
- Root endpoint behavior should be validated against Home Assistant startup logs in [config/home-assistant.log](config/home-assistant.log) when troubleshooting 404 or startup failures.
- pytest async fixture compatibility depends on [pytest.ini](pytest.ini) using asyncio_mode = auto.

## Test Guidance

- Prefer MockConfigEntry based tests for setup, unload, and config flow behavior.
- Patch IntegrationBlueprintApiClient async methods instead of calling external APIs.
- Keep tests deterministic and avoid network calls.

## References

- Home Assistant developer docs: https://developers.home-assistant.io/docs/creating_component_index
- DataUpdateCoordinator pattern: https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
- Test framework docs: https://github.com/MatthewFlamm/pytest-homeassistant-custom-component
