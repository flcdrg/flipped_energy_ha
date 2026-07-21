"""Flipped Energy authenticated portal scraping client."""

from __future__ import annotations

import asyncio
import datetime as dt
import math
import re
import socket
from contextlib import suppress
from http import HTTPStatus
from typing import Any
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from .const import (
    SNAPSHOT_AMOUNT_DUE_AUD,
    SNAPSHOT_AUTH_OK,
    SNAPSHOT_BILLING_PERIOD_END,
    SNAPSHOT_BILLING_PERIOD_START,
    SNAPSHOT_DATA_FRESH,
    SNAPSHOT_FEEDIN_RATE_CENTS,
    SNAPSHOT_IMPORT_RATE_CENTS,
    SNAPSHOT_LAST_SUCCESSFUL_SCRAPE,
    SNAPSHOT_PLAN_NAME,
    SNAPSHOT_TOTAL_FEEDIN_KWH,
    SNAPSHOT_TOTAL_USAGE_KWH,
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
    """Flipped Energy authenticated scraping client."""

    _BASE_URL = "https://flipped.energy"
    _LOGIN_PATH = "/accounts/login"
    _VALIDATE_PATH = "/accounts/"
    _PORTAL_PATHS = {
        "plan": "/accounts/plan",
        "usage": "/accounts/usage",
        "invoices": "/accounts/invoices",
    }
    _LABELS_USAGE_TODAY = ("usage today", "today usage", "daily usage")
    _LABELS_TOTAL_USAGE = ("total usage", "usage this period", "total consumption")
    _LABELS_TOTAL_FEEDIN = ("total feed-in", "total feed in", "feed in")
    _LABELS_AMOUNT_DUE = ("amount due", "total due", "current due")
    _LABELS_IMPORT_RATE = ("import rate", "usage rate", "energy rate")
    _LABELS_FEEDIN_RATE = ("feed-in rate", "feed in tariff", "solar feed-in")
    _LABELS_PERIOD_START = ("period start", "billing start", "from")
    _LABELS_PERIOD_END = ("period end", "billing end", "to")
    _PLAN_NAME_LABELS = ("plan name", "current plan")
    _STOP_LABELS = (
        "import rate",
        "feed-in rate",
        "feed in tariff",
        "usage today",
        "total usage",
        "total feed-in",
        "amount due",
        "period start",
        "period end",
    )

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        enabled_pages: dict[str, bool] | None = None,
    ) -> None:
        """Initialize the scraping client."""
        self._username = username
        self._password = password
        self._session = session
        self._authenticated = False
        enabled = enabled_pages or {
            "plan": True,
            "usage": True,
            "invoices": True,
        }
        if not any(enabled.values()):
            enabled["usage"] = True
        self._enabled_pages = enabled

    async def async_get_data(self) -> Any:
        """Authenticate and scrape a normalized account snapshot."""
        await self._ensure_authenticated()

        try:
            pages = {
                name: await self._fetch_page(path)
                for name, path in self._PORTAL_PATHS.items()
                if self._enabled_pages.get(name, False)
            }
        except IntegrationBlueprintApiClientAuthenticationError:
            self._authenticated = False
            await self._ensure_authenticated(force=True)
            pages = {
                name: await self._fetch_page(path)
                for name, path in self._PORTAL_PATHS.items()
                if self._enabled_pages.get(name, False)
            }

        snapshot = self._build_snapshot(pages)
        snapshot[SNAPSHOT_AUTH_OK] = True
        snapshot[SNAPSHOT_DATA_FRESH] = True
        snapshot[SNAPSHOT_LAST_SUCCESSFUL_SCRAPE] = dt.datetime.now(
            tz=dt.UTC
        ).isoformat()
        return snapshot

    async def _ensure_authenticated(self, force: bool = False) -> None:
        """Ensure portal session is authenticated."""
        if self._authenticated and not force:
            is_valid = await self._is_session_valid()
            if is_valid:
                return

        await self._login()
        self._authenticated = True

    async def _is_session_valid(self) -> bool:
        """Check whether the current session can access the account area."""
        async with self._session.get(
            urljoin(self._BASE_URL, self._VALIDATE_PATH),
            allow_redirects=True,
        ) as response:
            final_url = str(response.url)
            await response.read()
            if "/accounts/login" in final_url:
                return False
            return response.status == HTTPStatus.OK

    async def _login(self) -> None:
        """Authenticate against the portal."""
        login_url = urljoin(self._BASE_URL, self._LOGIN_PATH)

        login_page = await self._session.get(login_url, allow_redirects=True)
        _verify_response_or_raise(login_page)
        html = await login_page.text()
        csrf_token = self._extract_csrf_token(html)

        login_payload = {
            "username": self._username,
            "email": self._username,
            "password": self._password,
        }
        if csrf_token is not None:
            login_payload["__RequestVerificationToken"] = csrf_token

        response = await self._session.post(
            login_url,
            data=login_payload,
            allow_redirects=True,
        )
        if response.status in (401, 403):
            raise IntegrationBlueprintApiClientAuthenticationError(
                "Invalid credentials"
            )

        if "/accounts/login" in str(response.url):
            raise IntegrationBlueprintApiClientAuthenticationError(
                "Failed to authenticate with portal"
            )

        is_valid = await self._is_session_valid()
        if not is_valid:
            raise IntegrationBlueprintApiClientAuthenticationError(
                "Authenticated session is not valid"
            )

    async def _fetch_page(self, path: str) -> str:
        """Fetch and return a rendered page document."""
        response = await self._session.get(
            urljoin(self._BASE_URL, path), allow_redirects=True
        )
        if "/accounts/login" in str(response.url):
            raise IntegrationBlueprintApiClientAuthenticationError("Session expired")

        _verify_response_or_raise(response)
        return await response.text()

    def _build_snapshot(self, pages: dict[str, str]) -> dict[str, Any]:
        """Extract normalized values from portal pages."""
        plan_page = pages.get("plan", "")
        usage_page = pages.get("usage", "")
        invoices_page = pages.get("invoices", "")

        snapshot: dict[str, Any] = {
            SNAPSHOT_PLAN_NAME: self._extract_plan_name(plan_page),
            SNAPSHOT_USAGE_TODAY_KWH: self._extract_energy_value(
                usage_page,
                labels=self._LABELS_USAGE_TODAY,
            ),
            SNAPSHOT_TOTAL_USAGE_KWH: self._extract_energy_value(
                usage_page,
                labels=self._LABELS_TOTAL_USAGE,
            ),
            SNAPSHOT_TOTAL_FEEDIN_KWH: self._extract_energy_value(
                usage_page,
                labels=self._LABELS_TOTAL_FEEDIN,
            ),
            SNAPSHOT_AMOUNT_DUE_AUD: self._extract_money_value(
                invoices_page,
                labels=self._LABELS_AMOUNT_DUE,
            ),
            SNAPSHOT_IMPORT_RATE_CENTS: self._extract_rate_value(
                plan_page,
                labels=self._LABELS_IMPORT_RATE,
            ),
            SNAPSHOT_FEEDIN_RATE_CENTS: self._extract_rate_value(
                plan_page,
                labels=self._LABELS_FEEDIN_RATE,
            ),
            SNAPSHOT_BILLING_PERIOD_START: self._extract_period_value(
                invoices_page,
                labels=self._LABELS_PERIOD_START,
            ),
            SNAPSHOT_BILLING_PERIOD_END: self._extract_period_value(
                invoices_page,
                labels=self._LABELS_PERIOD_END,
            ),
        }

        required_fields: list[str] = []
        if self._enabled_pages.get("usage", False):
            required_fields.extend(
                [
                    SNAPSHOT_USAGE_TODAY_KWH,
                    SNAPSHOT_TOTAL_USAGE_KWH,
                    SNAPSHOT_TOTAL_FEEDIN_KWH,
                ]
            )
        if self._enabled_pages.get("invoices", False):
            required_fields.append(SNAPSHOT_AMOUNT_DUE_AUD)
        if self._enabled_pages.get("plan", False):
            required_fields.extend(
                [
                    SNAPSHOT_PLAN_NAME,
                    SNAPSHOT_IMPORT_RATE_CENTS,
                    SNAPSHOT_FEEDIN_RATE_CENTS,
                ]
            )

        missing_required_fields = [
            key for key in required_fields if snapshot.get(key) is None
        ]

        if missing_required_fields:
            raise IntegrationBlueprintApiClientExtractionError(
                "Unable to extract required fields from portal pages: "
                + ", ".join(missing_required_fields)
            )

        return snapshot

    def _extract_csrf_token(self, html: str) -> str | None:
        """Extract a CSRF token if present on login page."""
        soup = BeautifulSoup(html, "html.parser")
        for name in (
            "__RequestVerificationToken",
            "csrfmiddlewaretoken",
            "_token",
        ):
            token_input = soup.find("input", attrs={"name": name})
            if token_input and token_input.get("value"):
                return str(token_input["value"])
        return None

    def _extract_plan_name(self, html: str) -> str | None:
        """Extract a plan name from known labels or title fallback."""
        value = self._extract_labeled_text(
            html,
            labels=self._PLAN_NAME_LABELS,
            max_len=80,
        )
        if value:
            return value

        soup = BeautifulSoup(html, "html.parser")
        page_title = soup.title.string if soup.title and soup.title.string else None
        if not page_title:
            return None
        plan_title = page_title.replace("- Flipped Energy", "").strip()
        if plan_title.lower() == "plan details":
            return None
        return plan_title

    def _extract_money_value(self, html: str, labels: tuple[str, ...]) -> float | None:
        """Extract a dollar amount near matching labels."""
        return self._extract_number_near_labels(
            html,
            labels,
            pattern=r"\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        )

    def _extract_rate_value(self, html: str, labels: tuple[str, ...]) -> float | None:
        """Extract cents per kWh rate near labels."""
        return self._extract_number_near_labels(
            html,
            labels,
            pattern=r"([0-9]+(?:\.[0-9]+)?)\s*(?:c|¢)\s*/\s*kwh",
        )

    def _extract_energy_value(self, html: str, labels: tuple[str, ...]) -> float | None:
        """Extract kWh values near labels."""
        return self._extract_number_near_labels(
            html,
            labels,
            pattern=r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*kwh",
        )

    def _extract_period_value(self, html: str, labels: tuple[str, ...]) -> str | None:
        """Extract period boundary text for display as diagnostics."""
        return self._extract_labeled_text(html, labels=labels, max_len=32)

    def _extract_labeled_text(
        self,
        html: str,
        labels: tuple[str, ...],
        max_len: int,
    ) -> str | None:
        """Extract short human-readable value following a label."""
        text = self._to_text(html)
        for label in labels:
            regex = re.compile(
                rf"{re.escape(label)}\s*[:\-]?\s*([A-Za-z0-9\s\-/,.]+)",
                re.IGNORECASE,
            )
            match = regex.search(text)
            if not match:
                continue
            value = " ".join(match.group(1).split())
            value = self._trim_at_known_labels(value)
            if 0 < len(value) <= max_len:
                return value
        return None

    def _trim_at_known_labels(self, value: str) -> str:
        """Trim value when adjacent flattened text starts another known field."""
        lower_value = value.lower()
        cut_index = len(value)
        for stop_label in self._STOP_LABELS:
            idx = lower_value.find(stop_label)
            if idx > 0:
                cut_index = min(cut_index, idx)
        return value[:cut_index].strip(" :-,")

    def _extract_number_near_labels(
        self,
        html: str,
        labels: tuple[str, ...],
        pattern: str,
    ) -> float | None:
        """Extract a numeric value found near one of the provided labels."""
        text = self._to_text(html)
        for label in labels:
            regex = re.compile(
                rf"{re.escape(label)}[^\n]{{0,80}}?{pattern}",
                re.IGNORECASE,
            )
            match = regex.search(text)
            if not match:
                continue
            raw = match.group(1).replace(",", "")
            with suppress(ValueError):
                return float(raw)
        return None

    def _to_text(self, html: str) -> str:
        """Flatten HTML to normalized text for resilient matching."""
        soup = BeautifulSoup(html, "html.parser")
        return " ".join(soup.get_text(separator=" ", strip=True).split())

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
