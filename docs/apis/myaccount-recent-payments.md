# GET /MyAccount/RecentPayments

Purpose:

- Returns recent payment records.

URL:

- <https://api.flipped.energy/MyAccount/RecentPayments>

Auth:

- Bearer token required.

Request:

- Method: GET

Observed response shape:

- Root object with recentPayments array.

Observed status:

- 200

Notes:

- In observed HAR data, recentPayments was empty.
- Current integration does not map this endpoint into entities.
