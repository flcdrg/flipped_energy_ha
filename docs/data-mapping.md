# Flipped Energy Integration Data Mapping

This document traces each exposed Home Assistant entity field to the API payload field(s) and transform logic used by the integration.

## Source Endpoints

- POST /user/login
- GET /api/Tracing/correlation
- GET /MyAccount/ProjectAccountData
- GET /Usage/usage/projectreads/hourly
- GET /Usage/usage/projectreads/daily

## Sensor Field Mapping

| Snapshot key           | HA entity name                        | Primary API source               | Payload field(s)                                                                                        | Transform                                                                                                                                                  |
| ---------------------- | ------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| plan_name              | Flipped Energy Plan Name              | /MyAccount/ProjectAccountData    | accounts[0].productName, fallback accounts[0].product.name                                              | First non-empty text value.                                                                                                                                |
| amount_due_aud         | Flipped Energy Amount Due             | /MyAccount/ProjectAccountData    | First match among normalized keys: amountDue, totalAmountDue, amountOwing, balanceOwing, currentDue     | First numeric match returned. If isOverdue is false and no amount-like key exists, set 0.0.                                                                |
| usage_today_kwh        | Flipped Energy Usage (import)         | /Usage/usage/projectreads/hourly | rows where usageType=Export and date=time                                                               | Parse hourly timestamps; sum Export values for the latest completed day in the hourly window (API observed as retailer-perspective direction).             |
| usage_period_start     | Flipped Energy Usage (import)         | /Usage/usage/projectreads/hourly | earliest hourly export timestamp for the latest completed day                                           | First hourly export timestamp for the latest completed day.                                                                                                |
| usage_period_end       | Flipped Energy Usage Period End       | /Usage/usage/projectreads/hourly | latest completed day represented by hourly rows                                                         | Latest completed day as an ISO date string.                                                                                                                |
| total_usage_kwh        | Flipped Energy Total Usage (import)   | /Usage/usage/projectreads/daily  | rows where usageType=Export                                                                             | Sum abs(value) across Export rows; round to 6 decimals (API observed as retailer-perspective direction).                                                   |
| total_feedin_kwh       | Flipped Energy Total Feed-In (export) | /Usage/usage/projectreads/daily  | rows where usageType=Import                                                                             | Sum abs(value) across Import rows; round to 6 decimals.                                                                                                    |
| import_rate_cents_kwh  | Flipped Energy Import Rate            | /MyAccount/ProjectAccountData    | accounts[0].product.currentPlan.billingUnits[].chargePerKwh                                             | Exclude feed-in and non-positive units. Convert to c/kWh (x100). Use duration-weighted average when time-of-day windows are present, else arithmetic mean. |
| feedin_rate_cents_kwh  | Flipped Energy Feed-In Rate           | /MyAccount/ProjectAccountData    | accounts[0].product.currentPlan.billingUnits[] where billingUnitType=FeedInTariff or name contains feed | Convert chargePerKwh to c/kWh via abs(x100). Use minimum observed feed-in value.                                                                           |
| supply_charge_daily_cents | Flipped Energy Supply Charge Daily | /MyAccount/ProjectAccountData    | accounts[0].product.currentPlan.billingUnits[].periodicCharge on supply charge units                    | Convert dollars to cents when needed. Sensor output is dynamic: uses ex-GST or incl-GST based on the Include GST option.                                    |
| last_successful_update | Flipped Energy Last Successful Update | Integration runtime              | Not from payload                                                                                        | Set to current UTC timestamp after successful snapshot build.                                                                                              |

## Additional Snapshot Keys (Internal)

These keys are populated in coordinator data but are not currently exposed as standard sensors:

| Snapshot key         | Meaning                            | Source                                                                                                                                         |
| -------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| billing_period_start | Start date of billing/usage window | Prefer min usage row date from /Usage/usage/projectreads/daily. Fallback to nextBillIssueDate (YYYY-MM-DD) from /MyAccount/ProjectAccountData. |
| billing_period_end   | End date of billing/usage window   | Prefer max usage row date from /Usage/usage/projectreads/daily. Fallback to nextBillDueDate (YYYY-MM-DD) from /MyAccount/ProjectAccountData.   |
| import_rate_blocks   | Time-of-day import rate windows    | From usage billing units with timeOfDayStartMinutes/timeOfDayEndMinutes. Exposed as attributes on Flipped Energy Import Rate.                    |
| feedin_rate_blocks   | Time-of-day feed-in tariff windows | From feed-in billing units with timeOfDayStartMinutes/timeOfDayEndMinutes. Exposed as attributes on Flipped Energy Feed-In Rate.                 |
| supply_charge_daily_incl_gst_cents | Internal incl-GST supply value | Derived from supply billing units when available. Used as dynamic input when Include GST option is enabled.                                          |

## Binary Sensor Mapping

| Snapshot key | HA entity name               | Source              | Transform                                                                              |
| ------------ | ---------------------------- | ------------------- | -------------------------------------------------------------------------------------- |
| auth_ok      | Flipped Energy Authenticated | Integration runtime | Set true when login and required API extraction complete for the current update cycle. |
| data_fresh   | Flipped Energy Data Fresh    | Integration runtime | Set true when snapshot is freshly built without extraction/auth failure.               |

## Usage Endpoint Query Behavior

The integration explicitly queries usage endpoints with rolling UTC windows:

- /Usage/usage/projectreads/hourly
- /Usage/usage/projectreads/daily

- now-31d to now
- now-62d to now-31d
- now-14d to now

It stops after the first window that returns at least one valid row.

## UsageType Direction Note

Observed real-world payloads indicate `usageType` appears to be from the retailer/API perspective, not the customer dashboard perspective:

- API `Export` aligns with customer import usage (grid consumption).
- API `Import` aligns with customer feed-in export (solar export to grid).

The integration mapping above follows this observed direction so Home Assistant usage/feed-in entities align with customer-facing meter semantics.
