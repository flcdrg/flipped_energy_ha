# GET /Billing/meters

Purpose:
- Returns meter objects associated with the account.

URL:
- https://api.flipped.energy/Billing/meters

Auth:
- Bearer token required.

Request:
- Method: GET

Observed response shape:
- Root object with meters array.

Observed status:
- 200

Notes:
- In observed HAR, meters array was empty.
- Current integration does not use this endpoint for entity mapping.
