"""Flipped Energy authenticated API client."""

from __future__ import annotations

import asyncio
import datetime as dt
import math
import re
import socket
from contextlib import suppress
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode, urljoin

import aiohttp

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

from .const import (
    SNAPSHOT_AMOUNT_DUE_AUD,
    SNAPSHOT_AUTH_OK,
    SNAPSHOT_BILLING_PERIOD_END,
    SNAPSHOT_BILLING_PERIOD_START,
    SNAPSHOT_DATA_FRESH,
    SNAPSHOT_FEEDIN_RATE_BLOCKS,
    SNAPSHOT_FEEDIN_RATE_CENTS,
    SNAPSHOT_IMPORT_RATE_BLOCKS,
    SNAPSHOT_IMPORT_RATE_CENTS,
    SNAPSHOT_LAST_SUCCESSFUL_UPDATE,
    SNAPSHOT_PLAN_NAME,
    SNAPSHOT_SUPPLY_CHARGE_DAILY_CENTS,
    SNAPSHOT_SUPPLY_CHARGE_DAILY_INCL_GST_CENTS,
    SNAPSHOT_TOTAL_FEEDIN_KWH,
    SNAPSHOT_TOTAL_USAGE_KWH,
    SNAPSHOT_USAGE_DAILY_ROWS,
    SNAPSHOT_USAGE_FEEDIN_YESTERDAY_KWH,
    SNAPSHOT_USAGE_HOURLY_ROWS,
    SNAPSHOT_USAGE_PERIOD_END,
    SNAPSHOT_USAGE_PERIOD_START,
    SNAPSHOT_USAGE_TODAY_KWH,
)


class IntegrationBlueprintApiClientError(Exception):
    """Exception to indicate a general API error."""


class IntegrationBlueprintApiClientCommunicationError(
    IntegrationBlueprintApiClientError,
):
    """Exception to indicate a communication error."""


class IntegrationBlueprintApiClientAuthenticationError(
    IntegrationBlueprintApiClientError,
):
    """Exception to indicate an authentication error."""


class IntegrationBlueprintApiClientRateLimitError(
    IntegrationBlueprintApiClientCommunicationError,
):
    """Exception to indicate the API is rate limiting us."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        """Store the backoff period requested by the API."""
        super().__init__(message)
        self.retry_after = retry_after


class IntegrationBlueprintApiClientExtractionError(
    IntegrationBlueprintApiClientError,
):
    """Exception to indicate a page extraction error."""


def _parse_retry_after(response: aiohttp.ClientResponse) -> int:
    """Return the backoff period (whole seconds) from the Retry-After header."""
    value: float | None = None
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        with suppress(ValueError):
            value = float(retry_after)
    if value is not None and math.isfinite(value) and value >= 0:
        return math.ceil(value)
    return 60


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise IntegrationBlueprintApiClientAuthenticationError(
            msg,
        )
    if response.status == HTTPStatus.TOO_MANY_REQUESTS:
        msg = "Rate limited by the API"
        raise IntegrationBlueprintApiClientRateLimitError(
            msg,
            retry_after=_parse_retry_after(response),
        )
    response.raise_for_status()


class IntegrationBlueprintApiClient:
    """Flipped Energy authenticated API client."""

    _API_BASE_URL = "https://api.flipped.energy"
    _API_LOGIN_PATH = "/user/login"
    _API_VALIDATE_PATH = "/api/Tracing/correlation"
    _API_USAGE_HOURLY_PATH = "/Usage/usage/projectreads/hourly"
    _API_USAGE_DAILY_PATH = "/Usage/usage/projectreads/daily"
    _API_SNAPSHOT_PATHS = (
        "/MyAccount/GetAccountData",
        "/MyAccount/ProjectAccountData",
        "/MyAccount/landingpage",
        "/Billing/billing/index",
        "/Usage/usage/getreads",
        "/Usage/usage/getsettlements",
    )
    _RATE_DOLLARS_THRESHOLD = 2
    _CURRENCY_DOLLARS_THRESHOLD = 20
    _MINUTES_PER_HOUR = 60
    _TIME_COMPONENTS_HHMM = 2

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        enabled_pages: dict[str, bool] | None = None,
    ) -> None:
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._session = session
        self._authenticated = False
        self._auth_token: str | None = None
        enabled = enabled_pages or {
            "plan": True,
            "usage": True,
            "invoices": True,
        }
        if not any(enabled.values()):
            enabled["usage"] = True
        self._enabled_pages = enabled

    async def async_get_data(
        self,
        enabled_pages: dict[str, bool] | None = None,
    ) -> Any:
        """Authenticate and fetch a normalized account snapshot from APIs."""
        effective_pages = self._effective_enabled_pages(enabled_pages)
        await self._ensure_authenticated()

        try:
            snapshot = await self._augment_snapshot_from_api({}, effective_pages)
        except IntegrationBlueprintApiClientAuthenticationError:
            self._authenticated = False
            await self._ensure_authenticated(force=True)
            snapshot = await self._augment_snapshot_from_api({}, effective_pages)

        missing_required_fields = self._missing_required_fields(
            snapshot,
            effective_pages,
        )
        if missing_required_fields:
            raise IntegrationBlueprintApiClientExtractionError(
                "Unable to extract required fields from API responses: "
                + ", ".join(missing_required_fields)
            )

        snapshot[SNAPSHOT_AUTH_OK] = True
        snapshot[SNAPSHOT_DATA_FRESH] = True
        snapshot[SNAPSHOT_LAST_SUCCESSFUL_UPDATE] = dt.datetime.now(
            tz=dt.UTC
        ).isoformat()
        return snapshot

    def _effective_enabled_pages(
        self,
        enabled_pages: dict[str, bool] | None,
    ) -> dict[str, bool]:
        """Return a validated page selection for this fetch."""
        if enabled_pages is None:
            return dict(self._enabled_pages)

        effective = {
            "plan": bool(enabled_pages.get("plan", False)),
            "usage": bool(enabled_pages.get("usage", False)),
            "invoices": bool(enabled_pages.get("invoices", False)),
        }
        if not any(effective.values()):
            effective["usage"] = True
        return effective

    async def _ensure_authenticated(self, *, force: bool = False) -> None:
        """Ensure portal session is authenticated."""
        if self._authenticated and not force:
            is_valid = await self._is_session_valid()
            if is_valid:
                return

        await self._login()
        self._authenticated = True

    async def _is_session_valid(self) -> bool:
        """Check whether the current bearer token is still accepted by the API."""
        if not self._auth_token:
            return False

        async with self._session.get(
            urljoin(self._API_BASE_URL, self._API_VALIDATE_PATH),
            allow_redirects=False,
            headers={"Authorization": f"Bearer {self._auth_token}"},
        ) as response:
            await response.read()
            return response.status == HTTPStatus.OK

    async def _login(self) -> None:
        """Authenticate against the API used by the Flipped portal SPA."""
        login_url = urljoin(self._API_BASE_URL, self._API_LOGIN_PATH)

        response = await self._session.post(
            login_url,
            json={
                "email": self._username,
                "password": self._password,
            },
            allow_redirects=False,
            headers={"Content-Type": "application/json"},
        )

        if response.status in (400, 401, 403):
            msg = "Invalid credentials"
            raise IntegrationBlueprintApiClientAuthenticationError(msg)

        _verify_response_or_raise(response)

        payload = await response.json(content_type=None)
        token = payload.get("token") if isinstance(payload, dict) else None
        if not token or not isinstance(token, str):
            msg = "Login succeeded but no auth token was returned"
            raise IntegrationBlueprintApiClientAuthenticationError(msg)

        self._auth_token = token

        is_valid = await self._is_session_valid()
        if not is_valid:
            msg = "Authenticated token is not valid"
            raise IntegrationBlueprintApiClientAuthenticationError(msg)

    def _missing_required_fields(
        self,
        snapshot: dict[str, Any],
        enabled_pages: dict[str, bool],
    ) -> list[str]:
        """Return the required snapshot keys that are currently missing."""
        required_fields: list[str] = []
        if enabled_pages.get("usage", False):
            required_fields.extend(
                [
                    SNAPSHOT_USAGE_TODAY_KWH,
                    SNAPSHOT_TOTAL_USAGE_KWH,
                    SNAPSHOT_TOTAL_FEEDIN_KWH,
                ]
            )
        if enabled_pages.get("invoices", False):
            required_fields.append(SNAPSHOT_AMOUNT_DUE_AUD)
        if enabled_pages.get("plan", False):
            required_fields.extend(
                [
                    SNAPSHOT_PLAN_NAME,
                    SNAPSHOT_IMPORT_RATE_CENTS,
                    SNAPSHOT_FEEDIN_RATE_CENTS,
                ]
            )

        return [key for key in required_fields if snapshot.get(key) is None]

    async def _augment_snapshot_from_api(
        self,
        snapshot: dict[str, Any],
        enabled_pages: dict[str, bool],
    ) -> dict[str, Any]:
        """Fill missing snapshot fields from authenticated API responses."""
        payloads_by_path = await self._fetch_api_snapshot_payloads(enabled_pages)
        if not payloads_by_path:
            return snapshot

        mapped = self._map_snapshot_from_known_api_payloads(payloads_by_path)
        for key, value in mapped.items():
            if snapshot.get(key) is None and value is not None:
                snapshot[key] = value

        # Keep a final fuzzy pass to tolerate minor upstream schema changes.
        payloads = list(payloads_by_path.values())
        key_patterns: dict[str, tuple[tuple[str, ...], ...]] = {
            SNAPSHOT_AMOUNT_DUE_AUD: (
                ("amount", "due"),
                ("amount", "owing"),
                ("balance", "owing"),
            ),
            SNAPSHOT_IMPORT_RATE_CENTS: (("import", "rate"),),
            SNAPSHOT_FEEDIN_RATE_CENTS: (("feed", "in", "tariff"),),
        }
        for snapshot_key, patterns in key_patterns.items():
            if snapshot.get(snapshot_key) is not None:
                continue
            candidate = self._find_value_by_key_patterns(
                payloads,
                patterns,
                self._coerce_float,
            )
            if candidate is None:
                continue
            if snapshot_key in (SNAPSHOT_IMPORT_RATE_CENTS, SNAPSHOT_FEEDIN_RATE_CENTS):
                candidate = self._normalize_rate_candidate(candidate)
            snapshot[snapshot_key] = candidate

        return snapshot

    async def _fetch_api_snapshot_payloads(
        self,
        enabled_pages: dict[str, bool],
    ) -> dict[str, Any]:
        """Fetch candidate API payloads that may contain account snapshot data."""
        payloads_by_path: dict[str, Any] = {}
        if enabled_pages.get("plan", False) or enabled_pages.get("invoices", False):
            for path in self._API_SNAPSHOT_PATHS:
                try:
                    payload = await self._fetch_api_json(path)
                except IntegrationBlueprintApiClientError:
                    continue
                if payload is not None:
                    payloads_by_path[path] = payload

        # Hourly and daily usage are time-windowed in the web app; call them
        # explicitly with rolling windows to reliably obtain recent history.
        if enabled_pages.get("usage", False):
            hourly_rows = await self._fetch_usage_rows(self._API_USAGE_HOURLY_PATH)
            if hourly_rows:
                payloads_by_path[self._API_USAGE_HOURLY_PATH] = hourly_rows

            usage_rows = await self._fetch_daily_usage_rows()
            if usage_rows:
                payloads_by_path[self._API_USAGE_DAILY_PATH] = usage_rows

        return payloads_by_path

    async def _fetch_usage_rows(self, path: str) -> list[dict[str, Any]]:
        """Fetch usage rows from a time-windowed usage endpoint."""
        now = dt.datetime.now(dt.UTC)
        windows = [
            (now - dt.timedelta(days=31), now),
            (now - dt.timedelta(days=62), now - dt.timedelta(days=31)),
            (now - dt.timedelta(days=14), now),
        ]

        collected: list[dict[str, Any]] = []
        for start, end in windows:
            query = urlencode(
                {
                    "start": self._format_api_datetime(start),
                    "end": self._format_api_datetime(end),
                }
            )
            path_with_query = f"{path}?{query}"
            try:
                payload = await self._fetch_api_json(path_with_query)
            except IntegrationBlueprintApiClientError:
                continue

            if isinstance(payload, list):
                collected.extend(row for row in payload if isinstance(row, dict))

            if collected:
                break

        return collected

    async def _fetch_daily_usage_rows(self) -> list[dict[str, Any]]:
        """Fetch project daily usage rows using rolling UTC date windows."""
        return await self._fetch_usage_rows(self._API_USAGE_DAILY_PATH)

    def _format_api_datetime(self, value: dt.datetime) -> str:
        """Format UTC datetimes like the portal API query parameters."""
        return (
            value.astimezone(dt.UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

    def _map_snapshot_from_known_api_payloads(
        self,
        payloads_by_path: dict[str, Any],
    ) -> dict[str, Any]:
        """Map known API endpoint payloads into our normalized snapshot."""
        snapshot: dict[str, Any] = {}

        project_data = payloads_by_path.get("/MyAccount/ProjectAccountData")
        account = self._select_primary_account(project_data)
        if account:
            snapshot[SNAPSHOT_PLAN_NAME] = self._coerce_text(
                account.get("productName")
            ) or self._coerce_text((account.get("product") or {}).get("name"))

            rates = self._extract_rates_from_account(account)
            snapshot[SNAPSHOT_IMPORT_RATE_CENTS] = rates.get("import_rate_cents")
            snapshot[SNAPSHOT_FEEDIN_RATE_CENTS] = rates.get("feedin_rate_cents")
            snapshot[SNAPSHOT_IMPORT_RATE_BLOCKS] = rates.get("import_rate_blocks")
            snapshot[SNAPSHOT_FEEDIN_RATE_BLOCKS] = rates.get("feedin_rate_blocks")
            snapshot[SNAPSHOT_SUPPLY_CHARGE_DAILY_CENTS] = rates.get(
                "supply_charge_daily_cents"
            )
            snapshot[SNAPSHOT_SUPPLY_CHARGE_DAILY_INCL_GST_CENTS] = rates.get(
                "supply_charge_daily_incl_gst_cents"
            )

            amount_due = self._extract_amount_due_from_account(account)
            if amount_due is not None:
                snapshot[SNAPSHOT_AMOUNT_DUE_AUD] = amount_due

            issue_date = self._coerce_text(account.get("nextBillIssueDate"))
            due_date = self._coerce_text(account.get("nextBillDueDate"))
            if issue_date and snapshot.get(SNAPSHOT_BILLING_PERIOD_START) is None:
                snapshot[SNAPSHOT_BILLING_PERIOD_START] = issue_date[:10]
            if due_date and snapshot.get(SNAPSHOT_BILLING_PERIOD_END) is None:
                snapshot[SNAPSHOT_BILLING_PERIOD_END] = due_date[:10]

        usage_rows = payloads_by_path.get(self._API_USAGE_DAILY_PATH)
        usage_metrics = self._extract_usage_metrics(usage_rows)
        snapshot.update(usage_metrics)
        if isinstance(usage_rows, list):
            snapshot[SNAPSHOT_USAGE_DAILY_ROWS] = usage_rows

        hourly_rows = payloads_by_path.get(self._API_USAGE_HOURLY_PATH)
        hourly_metrics = self._extract_hourly_usage_metrics(hourly_rows)
        snapshot.update(hourly_metrics)
        if isinstance(hourly_rows, list):
            snapshot[SNAPSHOT_USAGE_HOURLY_ROWS] = hourly_rows

        return snapshot

    def _select_primary_account(self, project_data: Any) -> dict[str, Any] | None:
        """Select the primary account payload from ProjectAccountData."""
        if not isinstance(project_data, dict):
            return None
        accounts = project_data.get("accounts")
        if not isinstance(accounts, list) or not accounts:
            return None
        first = accounts[0]
        return first if isinstance(first, dict) else None

    def _extract_rates_from_account(  # noqa: PLR0912, PLR0915
        self, account: dict[str, Any]
    ) -> dict[str, float | list[dict[str, Any]] | None]:
        """Extract import/feed-in rates and supply charges from billing units."""
        current_plan = (account.get("product") or {}).get("currentPlan")
        if not isinstance(current_plan, dict):
            return {
                "import_rate_cents": None,
                "feedin_rate_cents": None,
                "import_rate_blocks": [],
                "feedin_rate_blocks": [],
                "supply_charge_daily_cents": None,
                "supply_charge_daily_incl_gst_cents": None,
            }

        billing_units = current_plan.get("billingUnits")
        if not isinstance(billing_units, list):
            return {
                "import_rate_cents": None,
                "feedin_rate_cents": None,
                "import_rate_blocks": [],
                "feedin_rate_blocks": [],
                "supply_charge_daily_cents": None,
                "supply_charge_daily_incl_gst_cents": None,
            }

        import_weighted_total = 0.0
        import_weight_total = 0.0
        import_flat_values: list[float] = []
        feed_in_values: list[float] = []
        import_rate_blocks: list[dict[str, Any]] = []
        feedin_rate_blocks: list[dict[str, Any]] = []
        supply_daily_excl_values: list[float] = []
        supply_daily_incl_values: list[float] = []

        for unit in billing_units:
            if not isinstance(unit, dict):
                continue

            if self._is_supply_charge_unit(unit):
                supply = self._extract_daily_supply_charge_from_unit(unit)
                if supply["excl_cents"] is not None:
                    supply_daily_excl_values.append(supply["excl_cents"])
                if supply["incl_cents"] is not None:
                    supply_daily_incl_values.append(supply["incl_cents"])
                continue

            charge = self._coerce_float(unit.get("chargePerKwh"))
            if charge is None:
                continue

            unit_type = self._coerce_text(unit.get("billingUnitType")) or ""
            name = (self._coerce_text(unit.get("name")) or "").lower()
            rate_block = self._build_rate_block(unit, charge)

            if unit_type == "FeedInTariff" or "feed" in name:
                feed_in_cents = abs(charge * 100)
                feed_in_values.append(feed_in_cents)
                if rate_block:
                    rate_block["rate_cents_kwh"] = round(feed_in_cents, 6)
                    feedin_rate_blocks.append(rate_block)
                continue

            if charge <= 0:
                continue

            duration = self._billing_unit_duration_minutes(unit)
            import_cents = charge * 100
            import_flat_values.append(import_cents)
            if duration is not None and duration > 0:
                import_weighted_total += import_cents * duration
                import_weight_total += duration
            if rate_block:
                rate_block["rate_cents_kwh"] = round(import_cents, 6)
                import_rate_blocks.append(rate_block)

        import_rate_cents: float | None = None
        if import_weight_total > 0:
            import_rate_cents = import_weighted_total / import_weight_total
        elif import_flat_values:
            import_rate_cents = sum(import_flat_values) / len(import_flat_values)

        feedin_rate_cents = min(feed_in_values) if feed_in_values else None
        supply_charge_daily_cents = (
            min(supply_daily_excl_values) if supply_daily_excl_values else None
        )
        supply_charge_daily_incl_gst_cents = (
            min(supply_daily_incl_values) if supply_daily_incl_values else None
        )

        return {
            "import_rate_cents": round(import_rate_cents, 6)
            if import_rate_cents is not None
            else None,
            "feedin_rate_cents": round(feedin_rate_cents, 6)
            if feedin_rate_cents is not None
            else None,
            "import_rate_blocks": self._sort_rate_blocks(import_rate_blocks),
            "feedin_rate_blocks": self._sort_rate_blocks(feedin_rate_blocks),
            "supply_charge_daily_cents": round(supply_charge_daily_cents, 6)
            if supply_charge_daily_cents is not None
            else None,
            "supply_charge_daily_incl_gst_cents": round(
                supply_charge_daily_incl_gst_cents,
                6,
            )
            if supply_charge_daily_incl_gst_cents is not None
            else None,
        }

    def _billing_unit_duration_minutes(self, unit: dict[str, Any]) -> int | None:
        """Return billing unit time-of-day duration in minutes."""
        start = unit.get("timeOfDayStartMinutes")
        end = unit.get("timeOfDayEndMinutes")
        if not isinstance(start, int) or not isinstance(end, int):
            return None
        if start == end:
            return 24 * 60
        if end > start:
            return end - start
        return (24 * 60 - start) + end

    def _is_supply_charge_unit(self, unit: dict[str, Any]) -> bool:
        """Return True when a billing unit represents a supply charge."""
        unit_type = (self._coerce_text(unit.get("billingUnitType")) or "").lower()
        name = (self._coerce_text(unit.get("name")) or "").lower()
        return "supply" in unit_type or "supply" in name

    def _extract_daily_supply_charge_from_unit(
        self,
        unit: dict[str, Any],
    ) -> dict[str, float | None]:
        """Extract daily supply charge values from a single billing unit."""
        period_text = (
            self._coerce_text(unit.get("period"))
            or self._coerce_text(unit.get("periodicity"))
            or self._coerce_text(unit.get("frequency"))
            or ""
        ).lower()
        if period_text and "day" not in period_text and "dail" not in period_text:
            return {"excl_cents": None, "incl_cents": None}

        unit_name = (self._coerce_text(unit.get("name")) or "").lower()
        periodic_charge = self._coerce_float(unit.get("periodicCharge"))
        charge_excl: float | None = None
        charge_incl: float | None = None
        if periodic_charge is not None:
            if "incl" in unit_name and "gst" in unit_name:
                charge_incl = periodic_charge
            else:
                charge_excl = periodic_charge

        if charge_incl is None:
            charge_incl = self._coerce_float(unit.get("periodicChargeInclGst"))
        if charge_incl is None:
            charge_incl = self._coerce_float(unit.get("periodicChargeIncludingGst"))

        if charge_excl is None and "excl" in unit_name and "gst" in unit_name:
            charge_excl = self._coerce_float(unit.get("chargePerKwh"))
        if charge_incl is None and "incl" in unit_name and "gst" in unit_name:
            charge_incl = self._coerce_float(unit.get("chargePerKwh"))

        excl_cents = self._normalize_currency_candidate_to_cents(charge_excl)
        incl_cents = self._normalize_currency_candidate_to_cents(charge_incl)

        if incl_cents is None and excl_cents is not None:
            gst_percent = self._coerce_float(unit.get("gstPercent"))
            if gst_percent is None:
                gst_percent = self._coerce_float(unit.get("gstPercentage"))
            if gst_percent is not None and gst_percent >= 0:
                incl_cents = excl_cents * (1 + gst_percent / 100)

        return {
            "excl_cents": round(excl_cents, 6) if excl_cents is not None else None,
            "incl_cents": round(incl_cents, 6) if incl_cents is not None else None,
        }

    def _normalize_currency_candidate_to_cents(
        self,
        value: float | None,
    ) -> float | None:
        """Normalize a currency value into cents, supporting dollars or cents."""
        if value is None:
            return None
        if abs(value) < self._CURRENCY_DOLLARS_THRESHOLD:
            return value * 100
        return value

    def _build_rate_block(
        self,
        unit: dict[str, Any],
        charge_per_kwh: float,
    ) -> dict[str, Any] | None:
        """Build a normalized time-of-day rate block for sensor attributes."""
        start = self._extract_time_of_day_minutes(unit, is_start=True)
        end = self._extract_time_of_day_minutes(unit, is_start=False)
        if start is None or end is None:
            return None

        block: dict[str, Any] = {
            "start_minutes": start,
            "end_minutes": end,
            "start_time": self._minutes_to_hhmm(start),
            "end_time": self._minutes_to_hhmm(end),
            "rate_cents_kwh": round(charge_per_kwh * 100, 6),
        }
        period_name = self._coerce_text(unit.get("name"))
        if period_name:
            block["name"] = period_name
        return block

    def _extract_time_of_day_minutes(
        self,
        unit: dict[str, Any],
        *,
        is_start: bool,
    ) -> int | None:
        """Extract time-of-day minute offset from multiple possible API keys."""
        keys = (
            ("timeOfDayStartMinutes", "timeOfDayEndMinutes")
            if is_start
            else ("timeOfDayEndMinutes", "timeOfDayStartMinutes")
        )
        alt_keys = (
            ("timeOfDayStart", "timeOfDayEnd")
            if is_start
            else ("timeOfDayEnd", "timeOfDayStart")
        )

        for key in keys + alt_keys:
            candidate = unit.get(key)
            minutes = self._coerce_minutes_value(candidate)
            if minutes is not None:
                return minutes

        return None

    def _coerce_minutes_value(self, value: Any) -> int | None:
        """Convert int/float or HH:MM strings to minutes since midnight."""
        if isinstance(value, bool):
            return None

        normalized: int | None = None
        if isinstance(value, int):
            normalized = value
        elif isinstance(value, float):
            normalized = int(value)
        elif isinstance(value, str):
            text = value.strip()
            if text:
                if text.isdigit():
                    normalized = int(text)
                else:
                    parts = text.split(":")
                    if len(parts) == self._TIME_COMPONENTS_HHMM:
                        with suppress(ValueError):
                            hours = int(parts[0])
                            minutes = int(parts[1])
                            if 0 <= minutes < self._MINUTES_PER_HOUR and hours >= 0:
                                normalized = (
                                    (hours % 24) * self._MINUTES_PER_HOUR
                                ) + minutes

        if normalized is None:
            return None
        return normalized % (24 * self._MINUTES_PER_HOUR)

    def _minutes_to_hhmm(self, total_minutes: int) -> str:
        """Convert minutes since midnight into HH:MM text."""
        normalized = total_minutes % (24 * 60)
        return f"{normalized // 60:02d}:{normalized % 60:02d}"

    def _sort_rate_blocks(self, blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort rate blocks by start/end minute for stable sensor attributes."""
        return sorted(
            blocks,
            key=lambda block: (
                block.get("start_minutes", 0),
                block.get("end_minutes", 0),
            ),
        )

    def _extract_amount_due_from_account(self, account: dict[str, Any]) -> float | None:
        """Extract amount due from account/invoice fields when available."""
        for key, value in self._walk_payload_key_values(account):
            normalized = self._normalize_key(key)
            if normalized in {
                "amountdue",
                "totalamountdue",
                "amountowing",
                "balanceowing",
                "currentdue",
            }:
                candidate = self._coerce_float(value)
                if candidate is not None:
                    return candidate

        is_overdue = account.get("isOverdue")
        if isinstance(is_overdue, bool) and not is_overdue:
            return 0.0

        return None

    def _extract_usage_metrics(self, usage_rows: Any) -> dict[str, Any]:
        """Extract usage totals and billing window from projectreads/daily rows."""
        if not isinstance(usage_rows, list):
            return {}

        customer_import_usage_rows: list[tuple[dt.date, float]] = []
        customer_feedin_rows: list[tuple[dt.date, float]] = []
        all_dates: list[dt.date] = []

        for row in usage_rows:
            if not isinstance(row, dict):
                continue
            stamp = self._coerce_text(row.get("time"))
            usage_type = (self._coerce_text(row.get("usageType")) or "").lower()
            value = self._coerce_float(row.get("value"))
            if not stamp or value is None:
                continue
            parsed_date = self._parse_iso_date(stamp)
            if parsed_date is None:
                continue

            all_dates.append(parsed_date)
            # Flipped usageType values are observed in retailer perspective:
            # - API Export corresponds to customer grid import (consumption)
            # - API Import corresponds to customer feed-in export
            if usage_type == "export":
                customer_import_usage_rows.append((parsed_date, abs(value)))
            elif usage_type == "import":
                customer_feedin_rows.append((parsed_date, abs(value)))

        if not all_dates:
            return {}

        metrics: dict[str, Any] = {
            SNAPSHOT_TOTAL_USAGE_KWH: round(
                sum(v for _, v in customer_import_usage_rows),
                6,
            )
            if customer_import_usage_rows
            else 0.0,
            SNAPSHOT_TOTAL_FEEDIN_KWH: round(sum(v for _, v in customer_feedin_rows), 6)
            if customer_feedin_rows
            else 0.0,
            SNAPSHOT_BILLING_PERIOD_START: min(all_dates).isoformat(),
            SNAPSHOT_BILLING_PERIOD_END: max(all_dates).isoformat(),
        }

        latest_date = max(
            (d for d, _ in customer_import_usage_rows),
            default=max(all_dates),
        )
        usage_today = sum(v for d, v in customer_import_usage_rows if d == latest_date)
        feedin_yesterday = sum(v for d, v in customer_feedin_rows if d == latest_date)
        metrics[SNAPSHOT_USAGE_TODAY_KWH] = round(usage_today, 6)
        metrics[SNAPSHOT_USAGE_FEEDIN_YESTERDAY_KWH] = round(feedin_yesterday, 6)
        return metrics

    def _extract_hourly_usage_metrics(self, usage_rows: Any) -> dict[str, Any]:
        """Extract the latest completed usage period from hourly rows."""
        if not isinstance(usage_rows, list):
            return {}

        hourly_customer_import_usage_rows: list[tuple[dt.datetime, float]] = []
        hourly_customer_feedin_rows: list[tuple[dt.datetime, float]] = []
        for row in usage_rows:
            if not isinstance(row, dict):
                continue
            stamp = self._coerce_text(row.get("time"))
            usage_type = (self._coerce_text(row.get("usageType")) or "").lower()
            value = self._coerce_float(row.get("value"))
            if not stamp or value is None:
                continue
            parsed_stamp = self._parse_iso_datetime(stamp)
            if parsed_stamp is None:
                continue
            # Flipped usageType is retailer-perspective; API Export is customer import.
            if usage_type == "export":
                hourly_customer_import_usage_rows.append((parsed_stamp, abs(value)))
            elif usage_type == "import":
                hourly_customer_feedin_rows.append((parsed_stamp, abs(value)))

        if not hourly_customer_import_usage_rows:
            return {}

        latest_date = max(
            stamp.date() for stamp, _ in hourly_customer_import_usage_rows
        )
        latest_period_rows = [
            (stamp, value)
            for stamp, value in hourly_customer_import_usage_rows
            if stamp.date() == latest_date
        ]
        latest_feedin_rows = [
            (stamp, value)
            for stamp, value in hourly_customer_feedin_rows
            if stamp.date() == latest_date
        ]
        if not latest_period_rows:
            return {}

        period_start = min(stamp for stamp, _ in latest_period_rows)

        return {
            SNAPSHOT_USAGE_TODAY_KWH: round(
                sum(value for _, value in latest_period_rows),
                6,
            ),
            SNAPSHOT_USAGE_FEEDIN_YESTERDAY_KWH: round(
                sum(value for _, value in latest_feedin_rows),
                6,
            ),
            SNAPSHOT_USAGE_PERIOD_START: period_start.isoformat(),
            SNAPSHOT_USAGE_PERIOD_END: latest_date.isoformat(),
        }

    def _parse_iso_datetime(self, value: str) -> dt.datetime | None:
        """Parse a timestamp/date string into a datetime value."""
        normalized = value.replace("Z", "+00:00")
        with suppress(ValueError):
            return dt.datetime.fromisoformat(normalized)
        return None

    def _parse_iso_date(self, value: str) -> dt.date | None:
        """Parse a timestamp/date into a date value."""
        normalized = value.replace("Z", "+00:00")
        with suppress(ValueError):
            return dt.datetime.fromisoformat(normalized).date()
        with suppress(ValueError):
            return dt.date.fromisoformat(value[:10])
        return None

    async def _fetch_api_json(self, path: str) -> Any:
        """Fetch JSON from an authenticated API path."""
        headers: dict[str, str] | None = None
        if self._auth_token:
            headers = {"Authorization": f"Bearer {self._auth_token}"}

        return await self._api_wrapper(
            method="GET",
            url=urljoin(self._API_BASE_URL, path),
            headers=headers,
        )

    def _find_value_by_key_patterns(
        self,
        payloads: list[Any],
        patterns: tuple[tuple[str, ...], ...],
        parser: Callable[[Any], float | None],
    ) -> Any | None:
        """Find the first value whose key matches one pattern and parses cleanly."""
        for key, value in self._walk_payload_key_values(payloads):
            normalized_key = self._normalize_key(key)
            if not any(
                all(part in normalized_key for part in pattern) for pattern in patterns
            ):
                continue
            parsed = parser(value)
            if parsed is not None:
                return parsed
        return None

    def _walk_payload_key_values(self, payload: Any) -> Iterator[tuple[str, Any]]:
        """Yield (key, value) pairs recursively from nested payload structures."""
        if isinstance(payload, dict):
            for key, value in payload.items():
                if isinstance(key, str):
                    yield key, value
                yield from self._walk_payload_key_values(value)
            return
        if isinstance(payload, list):
            for item in payload:
                yield from self._walk_payload_key_values(item)

    def _normalize_key(self, key: str) -> str:
        """Normalize payload keys for fuzzy semantic matching."""
        return re.sub(r"[^a-z0-9]", "", key.lower())

    def _coerce_float(self, value: Any) -> float | None:
        """Convert a scalar to float if possible."""
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"-?[0-9][0-9,]*(?:\.[0-9]+)?", value)
            if not match:
                return None
            raw = match.group(0).replace(",", "")
            with suppress(ValueError):
                return float(raw)
        return None

    def _coerce_text(self, value: Any) -> str | None:
        """Convert a scalar to trimmed text if possible."""
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        return text

    def _normalize_rate_candidate(self, value: float) -> float:
        """Normalize API rate values into cents/kWh when needed."""
        # Some APIs use dollars/kWh (e.g. 0.295); sensors expect cents/kWh.
        if 0 < value < self._RATE_DOLLARS_THRESHOLD:
            return round(value * 100, 6)
        return value

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Execute an HTTP request with typed error mapping."""
        try:
            async with asyncio.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                _verify_response_or_raise(response)
                return await response.json()

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(
                msg,
            ) from exception
        except IntegrationBlueprintApiClientError:
            # Our own typed errors (auth, rate-limit, communication) are already
            # meaningful; re-raise so callers can branch on them instead of masking
            # them with the broad handler below.
            raise
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise IntegrationBlueprintApiClientError(
                msg,
            ) from exception
