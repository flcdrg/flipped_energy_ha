# GET /Usage/usage/projectreads/daily

Purpose:

- Returns daily usage rows, including import/export values.

URL:

- <https://api.flipped.energy/Usage/usage/projectreads/daily>

Auth:

- Bearer token required.

Request:

- Method: GET
- Query parameters:
  - start: ISO-8601 datetime (UTC)
  - end: ISO-8601 datetime (UTC)

Observed row shape:

- time: string timestamp
- value: number
- usageType: string (Import or Export)
- controlledLoad: boolean
- nmi: string
- cost: number

Observed status:

- 200

Integration mapping:

- usage_today_kwh from Import rows for latest date
- total_usage_kwh from all Import row values in window
- total_feedin_kwh from all Export row values in window
- billing_period_start and billing_period_end from min/max row dates

Notes:

- Endpoint can return empty arrays for windows without data.
- Integration queries multiple rolling windows and stops once data is found.
