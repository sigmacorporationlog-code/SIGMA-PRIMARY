# QUALIFICATION_ENVIRONMENT — SIGMA PRIMARY P1

## Purpose

Document the exact environment used for the P1 qualification attempt. No missing dependency or unavailable service is counted as PASS.

## Application requirements

- Python requirement: no exact minor version pinned by the application requirement file; runtime tested with Python **3.13.5**.
- `bcrypt`: requirement **>=4.1,<5**. No lock file exists, therefore no exact bcrypt patch version is frozen by the repository.
- Pytest build requirement: **>=8,<9**.
- PostgreSQL driver: `psycopg[binary]>=3.2,<4`.
- Redis client: `redis>=5,<8`.
- Android Gradle wrapper target: **Gradle 8.9**.

## Host used for qualification attempt

- OS: Linux x86_64, kernel `6.18.44-...`.
- Python: **3.13.5**.
- Node.js: **22.16.0**.
- Java: **21.0.11**.
- Pytest available globally: **9.0.2** (outside project requirement `<9`; therefore the host is not a compliant frozen build environment).
- FastAPI: **0.128.2**.
- SQLAlchemy: **2.0.50**.
- Alembic: **1.18.4**.
- Pydantic: **2.13.4**.
- PyJWT: **2.13.0**.
- `openpyxl`: **3.1.5**.
- ReportLab: **4.4.9**.
- Pillow: **12.3.0**.
- pypdf: **5.9.0**.
- python-docx: **1.2.0**.
- httpx: **0.28.1**.

## Fresh qualification venv

A fresh Python 3.13.5 virtual environment was created at `p1_remediation/venv`.

Attempted commands:

```text
python -m venv venv
venv/bin/python -m pip install --upgrade pip setuptools wheel
venv/bin/python -m pip install -r requirements.txt -r requirements-build.txt
```

The dependency installation could not complete because external DNS/network access is unavailable. A direct verification attempt for bcrypt failed with:

```text
Temporary failure in name resolution
Could not find a version that satisfies the requirement bcrypt<5,>=4.1
```

Therefore the fresh qualification environment is **BLOCKED — ENVIRONMENT NOT AVAILABLE**. No package was mocked or vendored to manufacture a PASS.

## Full Python test suite evidence

From the application root, excluding only `tests/test_v446_correction_actions.py` because that module cannot even be collected without bcrypt:

```text
437 tests collected
430 passed
7 failed
```

The seven failing tests are identical between the H4 baseline and the P1-fixed workspace, proving the P1 changes did not add a regression in that comparison set. Three of those seven are directly blocked by missing bcrypt during test subprocess setup.

The complete suite cannot be called PASS because the four tests in the excluded module were not collected and the required runtime dependencies are not installed.

## Browser

Chromium is installed at `/usr/bin/chromium`, but the headless qualification harness did not terminate successfully in this container. Browser-level XSS execution is therefore **BLOCKED — ENVIRONMENT UNSTABLE** and not counted as a PASS.

## PostgreSQL

- `psql`: not installed.
- `pg_isready`: not installed.
- TCP `127.0.0.1:5432`: connection refused.
- Docker CLI/daemon: not installed/available.

Status: **BLOCKED — REAL POSTGRESQL NOT AVAILABLE**.

## Redis

- `redis-cli`: not installed.
- `redis-server`: not installed.
- TCP `127.0.0.1:6379`: connection refused.

Status: **BLOCKED — REAL REDIS NOT AVAILABLE**.

## Android

- Java 21 available.
- Android SDK/`adb`: unavailable.
- `sdkmanager`: unavailable.
- Gradle wrapper exists and targets Gradle 8.9, but the wrapper attempted to download the distribution from `services.gradle.org` and failed with `UnknownHostException`.

Status: **BLOCKED — ANDROID SDK/GRADLE DISTRIBUTION UNAVAILABLE**.
