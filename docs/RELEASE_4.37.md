# SIGMA V4.37 — Enterprise Data & End-to-End Qualification

V4.37 introduces a deterministic qualification harness for the core academic workflow.

## Qualification coverage

- two isolated schools in one test dataset;
- academic year and period creation;
- classes, students and memberships;
- subjects and teacher assignments;
- assessments and validated grades;
- general-average calculation;
- class ranking;
- report-card persistence;
- explicit tenant-isolation invariant;
- machine-readable JSON report and HTML report.

## Run

```powershell
python scripts/qualification_suite.py
```

Optional outputs:

```powershell
python scripts/qualification_suite.py --output qualification.json --html-output qualification.html
```

The harness is deliberately isolated and does not seed production data. `QUALIFIED` means the deterministic qualification scenarios passed in the environment where the command was executed; it does not certify PostgreSQL or Windows until those environments are tested with their real runtime dependencies.
