# PYTHON DEPENDENCY MATRIX

| PACKAGE | REQUIRED VERSION | INSTALLED / AVAILABLE | STATUS | TEST RESULT |
|---|---|---|---|---|
| fastapi | >=0.115,<1 | 0.128.2 | PASS | import/tests available |
| uvicorn | >=0.30,<1 | 0.48.0 | PASS | package available |
| python-multipart | >=0.0.9,<1 | 0.0.29 | PASS | package available |
| pydantic | >=2.7,<3 | 2.13.4 | PASS | tests available |
| pydantic-settings | >=2.2,<3 | 2.14.1 | PASS | tests available |
| email-validator | >=2.1,<3 | 2.3.0 | PASS | auth schema import available |
| sqlalchemy | >=2,<3 | 2.0.50 | PASS | DB tests available |
| alembic | >=1.13,<2 | 1.18.4 | PASS | migration roundtrip PASS |
| psycopg | >=3.2,<4 | MISSING | BLOCKED | PostgreSQL tests blocked |
| python-jose[cryptography] | >=3.3,<4 | MISSING | BLOCKED | app import/security subprocesses blocked |
| bcrypt | >=4.1,<5 | 4.2.0 system package | PARTIAL | usable through qualification compatibility path |
| cryptography | >=42,<47 | 46.0.4 Python env / 43.0.0 system | PASS | cryptographic static tests PASS |
| openpyxl | >=3.1,<4 | 3.1.5 | PASS | package available |
| reportlab | >=4,<5 | 4.4.9 | PASS | package available |
| pillow | >=10,<13 | 12.3.0 | PASS | package available |
| qrcode | >=7.4,<9 | 8.2 | PASS | package available |
| pypdf | >=5,<7 | 5.9.0 | PASS | package available |
| python-docx | >=1.1,<2 | 1.2.0 | PASS | package available |
| redis | >=5,<8 | 6.1.0 system package | PARTIAL | no real Redis server |
| pywebpush | >=2,<3 | MISSING | BLOCKED | push integration unavailable |
| httpx | >=0.27,<1 | 0.28.1 | PASS | package available |
| pytest | >=8,<9 | 9.0.2 | WRONG_VERSION | suite executed, release qualification should use project range |
| pytest-asyncio | >=0.24,<1 | 1.3.0 | PASS | available |
