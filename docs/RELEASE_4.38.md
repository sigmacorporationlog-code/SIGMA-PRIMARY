# SIGMA V4.38 — SLA, Central Monitoring & Operational Alerting

V4.38 adds operational SLA reporting without overstating contractual availability.

## Added
- `/api/system/sla/current`: observed API availability, 5xx rate, latency percentiles and high/critical incident downtime for the selected month.
- `/api/system/sla/alerts`: threshold-based operational alerts for 5xx rate and p95 latency.
- Configurable `SLA_TARGET_PERCENT`, `SLA_MAX_5XX_PERCENT`, `SLA_MAX_P95_MS`.

## Important qualification rule
The report is explicitly `mode=observed` and `contractual_sla_claim=false`. An in-process metric collector cannot by itself prove contractual uptime across restarts, network failures or external dependencies.
