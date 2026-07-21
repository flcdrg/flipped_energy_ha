# Flipped Energy integration for Home Assistant

## What?

This repository contains multiple files, here is a overview:

File | Purpose | Documentation
-- | -- | --
`.devcontainer.json` | Used for development/testing with Visual Studio Code. | [Documentation](https://code.visualstudio.com/docs/remote/containers)
`.github/renovate.json` | Dependency update configuration for Renovate (enabled by default). | [Documentation](https://docs.renovatebot.com/configuration-options/)
`.github/_dependabot.yml` | Dependency update configuration for Dependabot (disabled, see "Dependency updates" below). | [Documentation](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file)
`.github/ISSUE_TEMPLATE/*.yml` | Templates for the issue tracker | [Documentation](https://help.github.com/en/github/building-a-strong-community/configuring-issue-templates-for-your-repository)
`custom_components/flipped_energy/*` | Integration files, this is where everything happens. | [Documentation](https://developers.home-assistant.io/docs/creating_component_index)
`CONTRIBUTING.md` | Guidelines on how to contribute. | [Documentation](https://help.github.com/en/github/building-a-strong-community/setting-guidelines-for-repository-contributors)
`LICENSE` | The license file for the project. | [Documentation](https://help.github.com/en/github/creating-cloning-and-archiving-repositories/licensing-a-repository)
`README.md` | The file you are reading now, should contain info about the integration, installation and configuration instructions. | [Documentation](https://help.github.com/en/github/writing-on-github/basic-writing-and-formatting-syntax)
`requirements_dev.txt` | Python packages used for development/testing this integration (also installs lint tooling via `requirements_lint.txt`). | [Documentation](https://pip.pypa.io/en/stable/user_guide/#requirements-files)
`requirements_lint.txt` | Python packages used to lint this integration (installed by the Lint CI job). | [Documentation](https://pip.pypa.io/en/stable/user_guide/#requirements-files)
`requirements_common.txt` | Python packages common to CI and local dev, installed first so any pip upgrade completes before other dependencies (e.g. a modern pip). | [Documentation](https://pip.pypa.io/en/stable/user_guide/#requirements-files)

## How?


1. Run the `scripts/develop` to start HA and test out your new integration.

## Next steps

These are some next steps you may want to look into:
- Run `./scripts/test` to execute the included integration tests, and extend coverage using [`pytest-homeassistant-custom-component`](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component).
- Add brand images (logo/icon).
- Create your first release.
- Share your integration on the [Home Assistant Forum](https://community.home-assistant.io/).
- Submit your integration to [HACS](https://hacs.xyz/docs/publish/start).
