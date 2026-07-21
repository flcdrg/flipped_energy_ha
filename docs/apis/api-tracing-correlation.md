# GET /api/Tracing/correlation

Purpose:

- Lightweight authenticated endpoint used to validate that bearer token is still valid.

URL:

- <https://api.flipped.energy/api/Tracing/correlation>

Auth:

- Bearer token required in Authorization header.

Request:

- Method: GET

Observed responses:

- 200: token accepted
- 401 or 403: token invalid/expired

Notes:

- Integration uses this as its session validity check before data fetch.
