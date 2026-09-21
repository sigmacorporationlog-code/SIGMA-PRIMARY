# SMS Provider Audit — SIGMA PRIMARY

## Provider states
- `FakeSmsProvider`: deterministic simulation for tests/development.
- `HttpSmsProvider`: real HTTP provider integration path.
- Additional providers can implement the same provider contract.

## Production safety
- `SMS_ALLOW_SIMULATION_IN_PRODUCTION` defaults to `false`.
- Fake provider in production is rejected unless explicitly and intentionally enabled by configuration.
- Simulation responses carry explicit `simulated` state.

## Operational state
Delivery status includes provider/status/error context and can be surfaced to support tooling.

## Verification
Targeted SMS/provider tests pass.

## Residual risk
A real provider contract still needs a live sandbox/integration test with the provider credentials available; this environment does not contain such credentials.
