# GET /MyAccount/GetPaymentMethods

Purpose:

- Returns configured payment methods for the account.

URL:

- <https://api.flipped.energy/MyAccount/GetPaymentMethods>

Auth:

- Bearer token required.

Request:

- Method: GET

Observed response shape:

- Root object with paymentMethods array.
- Each item may include:
  - paymentMethodId
  - type
  - displayName
  - accountName
  - bsb
  - accountNumbers
  - accountActiveStatus
  - directDebitAccepted
  - directDebitAuthorised
  - precedence

Observed status:

- 200

Notes:

- Current integration does not map these values to entities yet.
