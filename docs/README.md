# Flipped Energy API Docs

This folder documents the Flipped Energy APIs observed in this repository and in captured browser HAR traffic. It is not official documentation of these APIs.

Scope:

- Base URL: <https://api.flipped.energy>
- Authentication: Bearer token from login endpoint
- Source of truth for this documentation:
  - Integration client implementation

Important:

- These APIs are not official public APIs in this repository context.
- Behavior can change without notice.
- Treat all examples as implementation guidance, not a contract.

## Endpoint Index

Authentication and session:

- [POST /user/login](apis/user-login.md)
- [GET /api/Tracing/correlation](apis/api-tracing-correlation.md)

Account and billing:

- [GET /MyAccount/ProjectAccountData](apis/myaccount-project-account-data.md)
- [GET /MyAccount/GetPaymentMethods](apis/myaccount-get-payment-methods.md)
- [GET /MyAccount/user](apis/myaccount-user.md)
- [GET /MyAccount/RecentPayments](apis/myaccount-recent-payments.md)
- [GET /Billing/meters](apis/billing-meters.md)

Usage:

- [GET /Usage/usage/projectreads/daily](apis/usage-projectreads-daily.md)
- [GET /Usage/usage/projectreads/hourly](apis/usage-projectreads-hourly.md)
- [GET /Usage/usage/projectreads/weekly](apis/usage-projectreads-weekly.md)
- [GET /Usage/usage/projectreads/monthly](apis/usage-projectreads-monthly.md)

Supporting endpoints seen in HAR:

- [GET /home/webconfig](apis/home-webconfig.md)
- [GET /crisp/hmac](apis/crisp-hmac.md)

## Endpoint Matrix

| Method | Path                              | Auth                            | Used by integration | Notes                                                                    |
| ------ | --------------------------------- | ------------------------------- | ------------------- | ------------------------------------------------------------------------ |
| POST   | /user/login                       | None (credential login request) | Yes                 | Returns bearer token used for subsequent requests.                       |
| GET    | /api/Tracing/correlation          | Bearer                          | Yes                 | Used as token validity check.                                            |
| GET    | /MyAccount/ProjectAccountData     | Bearer                          | Yes                 | Primary account, plan, rates, and bill-date source.                      |
| GET    | /Usage/usage/projectreads/hourly  | Bearer                          | Yes                 | Historical usage sensor source; provides usage amount and period dates.  |
| GET    | /Usage/usage/projectreads/daily   | Bearer                          | Yes                 | Usage totals, feed-in totals, latest-day usage, billing range from rows. |
| GET    | /Usage/usage/projectreads/weekly  | Bearer                          | No                  | Weekly usage endpoint observed in portal traffic.                        |
| GET    | /Usage/usage/projectreads/monthly | Bearer                          | No                  | Monthly usage endpoint observed in portal traffic.                       |
| GET    | /MyAccount/GetPaymentMethods      | Bearer                          | No                  | Observed in portal traffic; currently not mapped to entities.            |
| GET    | /MyAccount/user                   | Bearer                          | No                  | Profile data endpoint, not currently exposed in HA entities.             |
| GET    | /MyAccount/RecentPayments         | Bearer                          | No                  | Recent payment history endpoint, currently unused.                       |
| GET    | /Billing/meters                   | Bearer                          | No                  | Meter metadata endpoint, currently unused.                               |
| GET    | /home/webconfig                   | Session/bootstrap traffic       | No                  | Frontend web configuration endpoint.                                     |
| GET    | /crisp/hmac                       | Session context                 | No                  | Crisp chat integration support endpoint.                                 |

## Data Mapping

- Entity-level mappings and field transforms are documented in [Data Mapping](data-mapping.md).

## Current Integration Mapping

The Home Assistant integration currently derives values from:

- Plan name: MyAccount ProjectAccountData
- Import and feed-in rates: product.currentPlan.billingUnits
- Amount due: account amount-like fields (fallback to 0 when not overdue)
- Usage: Usage projectreads hourly
- Usage period metadata: Usage projectreads hourly
- Total usage, total feed-in: Usage projectreads daily
- Billing period start/end: usage date range or next bill fields
