# Academic Engine Audit — SIGMA PRIMARY

## Current architecture
The academic engine now distinguishes:
1. raw grades and coefficients;
2. weighted calculations;
3. normalization;
4. explicit rounding;
5. presentation.

## Numeric policy
- Database storage: NUMERIC/Decimal for academic/evaluation values migrated by 6320.
- Application arithmetic: `Decimal`.
- Final display/rounding: `ROUND_HALF_UP` to the documented precision.
- Invalid financial values above the supported decimal scale are rejected rather than silently coerced.

## GPA
Two explicit modes are available:
- `overall_scale`: preserves the previous global-percent-to-GPA behavior.
- `subject_weighted`: computes GPA from subject-level grade points and weights.

No claim is made that one GPA convention is universally correct; the selected mode is a school configuration decision.

## Verification
- Academic targeted tests: PASS.
- GPA mode tests: PASS.
- Fresh migration + downgrade/upgrade cycles: PASS.
- Qualification suite after Decimal migration: PASS after making the qualification report JSON-safe for Decimal values.

## Residual risk
External school-system compatibility rules still require per-school configuration and reference examples; no single GPA policy is imposed as universally valid.
