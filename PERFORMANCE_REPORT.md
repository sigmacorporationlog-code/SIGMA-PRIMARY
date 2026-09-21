# PERFORMANCE REPORT — P2/P3

## Query-shape hardening
- Grade entry/upsert flow batch-fetches students, existing grades and sync versions.
- Teacher assignment list batches related users/subjects.
- Dashboard evolution/statistics use database-side aggregation.
- Honor-board ranking is calculated in a bounded query shape.

## Reproducible benchmark (SQLite in-memory)
| Students | SQL statements | Time (ms) | Queries/student |
|---:|---:|---:|---:|
| 100 | 3 | 4.06 | 0.03 |
| 500 | 3 | 8.01 | 0.006 |
| 1,000 | 3 | 10.44 | 0.003 |
| 5,000 | 3 | 47.59 | 0.0006 |

These are local SQLite benchmark numbers, not PostgreSQL/load-test certification.

## Remaining performance work
- PostgreSQL EXPLAIN/ANALYZE with production-like indexes.
- Concurrent writer/read tests.
- Redis-backed cache/queue behavior under load.
- 10,000+ student scenarios where relevant.
- PDF and import/export load tests.
