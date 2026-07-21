# GET /Usage/usage/projectreads/weekly

Purpose:

- Returns weekly usage rows seen in portal traffic.

URL:

- <https://api.flipped.energy/Usage/usage/projectreads/weekly>

Auth:

- Bearer token required.

Request:

- Method: GET
- Query parameters:
  - start: ISO-8601 datetime (UTC)
  - end: ISO-8601 datetime (UTC)

Observed row shape:

- Same `time`, `value`, `usageType`, `controlledLoad`, `nmi`, `cost` shape as the other usage endpoints.

Observed status:

- 200

Notes:

- Currently documented from HAR only; not consumed by the integration.
