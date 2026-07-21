# GET /MyAccount/user

Purpose:

- Returns user profile information for the authenticated account.

URL:

- <https://api.flipped.energy/MyAccount/user>

Auth:

- Bearer token required.

Request:

- Method: GET

Observed response fields:

- id
- email
- firstName
- lastName
- phoneNumber
- dob
- emailConfirmed
- state

Observed status:

- 200

Notes:

- Current integration does not expose profile fields as entities.
