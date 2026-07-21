# GET /MyAccount/ProjectAccountData

Purpose:

- Primary account dataset for account, product, billing, and contract information.

URL:

- <https://api.flipped.energy/MyAccount/ProjectAccountData>

Auth:

- Bearer token required.

Request:

- Method: GET

Observed response shape:

- Root object with accounts array.
- accounts[0] contains fields such as:
  - accountNumber
  - billingPeriod
  - productName
  - nextBillIssueDate
  - nextBillDueDate
  - isOverdue
  - product.currentPlan.billingUnits[]

Useful billing unit fields:

- billingUnitType
- name
- chargePerKwh
- periodicCharge
- timeOfDayStartMinutes
- timeOfDayEndMinutes

Integration mapping:

- plan_name from productName
- import_rate_cents_kwh derived from positive chargePerKwh units
- feedin_rate_cents_kwh derived from FeedInTariff units
- amount_due_aud inferred from amount-like fields if present, else 0 when not overdue
- billing_period_start and billing_period_end may fallback to nextBillIssueDate/nextBillDueDate

Observed status:

- 200
