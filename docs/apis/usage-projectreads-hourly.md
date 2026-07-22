# GET /Usage/usage/projectreads/hourly

Purpose:

- Returns hourly usage rows used to surface the integration's historical usage sensor.

URL:

- <https://api.flipped.energy/Usage/usage/projectreads/hourly>

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

- usage_today_kwh from Export rows for the latest completed day in the hourly window
- usage_period_start from the earliest hourly export timestamp in that day
- usage_period_end from the latest completed day date

Notes:

- Endpoint can return empty arrays for windows without data.
- Integration queries multiple rolling windows and stops once data is found.
- Observed payloads suggest `usageType` is retailer-perspective (`Export`=customer import, `Import`=customer feed-in).
