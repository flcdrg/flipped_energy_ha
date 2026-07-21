#!/usr/bin/env python3
"""Run a real-site Flipped Energy API fetch and print the normalized snapshot."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import sys
from pathlib import Path

import aiohttp

# Ensure local integration package is importable when executed from scripts/.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from custom_components.flipped_energy.api import (  # noqa: E402
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientCommunicationError,
    IntegrationBlueprintApiClientError,
    IntegrationBlueprintApiClientExtractionError,
    IntegrationBlueprintApiClientRateLimitError,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Authenticate against https://flipped.energy and print the normalized "
            "snapshot returned by the integration client."
        )
    )
    parser.add_argument(
        "--username",
        required=True,
        help="Flipped Energy account email/username",
    )
    parser.add_argument(
        "--password",
        help="Flipped Energy password (if omitted, prompt securely)",
    )
    parser.add_argument(
        "--include-plan",
        action="store_true",
        default=False,
        help="Include plan data fetch",
    )
    parser.add_argument(
        "--include-usage",
        action="store_true",
        default=False,
        help="Include usage data fetch",
    )
    parser.add_argument(
        "--include-invoices",
        action="store_true",
        default=False,
        help="Include invoice data fetch",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Total aiohttp timeout in seconds (default: 20)",
    )
    return parser


def _resolve_enabled_pages(args: argparse.Namespace) -> dict[str, bool]:
    enabled = {
        "plan": args.include_plan,
        "usage": args.include_usage,
        "invoices": args.include_invoices,
    }
    if not any(enabled.values()):
        return {"plan": True, "usage": True, "invoices": True}
    return enabled


async def _run(args: argparse.Namespace) -> int:
    password = args.password or getpass.getpass("Flipped Energy password: ")
    enabled_pages = _resolve_enabled_pages(args)

    timeout = aiohttp.ClientTimeout(total=args.timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        client = IntegrationBlueprintApiClient(
            username=args.username,
            password=password,
            session=session,
            enabled_pages=enabled_pages,
        )

        try:
            snapshot = await client.async_get_data()
        except IntegrationBlueprintApiClientAuthenticationError as err:
            print(f"Authentication failed: {err}", file=sys.stderr)
            return 2
        except IntegrationBlueprintApiClientRateLimitError as err:
            retry_after = (
                f" Retry after {err.retry_after}s."
                if err.retry_after is not None
                else ""
            )
            print(f"Rate limited: {err}.{retry_after}", file=sys.stderr)
            return 3
        except IntegrationBlueprintApiClientExtractionError as err:
            print(f"API data extraction failed: {err}", file=sys.stderr)
            return 4
        except IntegrationBlueprintApiClientCommunicationError as err:
            print(f"Network/communication error: {err}", file=sys.stderr)
            return 5
        except IntegrationBlueprintApiClientError as err:
            print(f"API error: {err}", file=sys.stderr)
            return 6

    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


def main() -> int:
    """Run the CLI entrypoint."""
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
