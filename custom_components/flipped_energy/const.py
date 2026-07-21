"""Constants for flipped_energy."""

from datetime import timedelta
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "flipped_energy"
ATTRIBUTION = "Data provided by Flipped Energy portal pages"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

CONF_REFRESH_INTERVAL_MINUTES = "refresh_interval_minutes"
CONF_ENABLE_PLAN_PAGE = "enable_plan_page"
CONF_ENABLE_USAGE_PAGE = "enable_usage_page"
CONF_ENABLE_INVOICES_PAGE = "enable_invoices_page"

DEFAULT_REFRESH_INTERVAL_MINUTES = 30
MIN_REFRESH_INTERVAL_MINUTES = 5
MAX_REFRESH_INTERVAL_MINUTES = 180

SNAPSHOT_PLAN_NAME = "plan_name"
SNAPSHOT_AMOUNT_DUE_AUD = "amount_due_aud"
SNAPSHOT_USAGE_TODAY_KWH = "usage_today_kwh"
SNAPSHOT_TOTAL_USAGE_KWH = "total_usage_kwh"
SNAPSHOT_TOTAL_FEEDIN_KWH = "total_feedin_kwh"
SNAPSHOT_IMPORT_RATE_CENTS = "import_rate_cents_kwh"
SNAPSHOT_FEEDIN_RATE_CENTS = "feedin_rate_cents_kwh"
SNAPSHOT_BILLING_PERIOD_START = "billing_period_start"
SNAPSHOT_BILLING_PERIOD_END = "billing_period_end"
SNAPSHOT_AUTH_OK = "auth_ok"
SNAPSHOT_DATA_FRESH = "data_fresh"
SNAPSHOT_LAST_SUCCESSFUL_SCRAPE = "last_successful_scrape"
