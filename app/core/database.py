from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False, "isolation_level": "IMMEDIATE"} if is_sqlite else {}
engine_kwargs = {"pool_pre_ping": True, "future": True, "connect_args": connect_args}
if not is_sqlite:
    engine_kwargs.update({
        "pool_size": max(1, settings.DB_POOL_SIZE),
        "max_overflow": max(0, settings.DB_MAX_OVERFLOW),
        "pool_timeout": max(1, settings.DB_POOL_TIMEOUT_SECONDS),
        "pool_recycle": max(60, settings.DB_POOL_RECYCLE_SECONDS),
    })
engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

if is_sqlite:
    # SQLite désactive les contraintes de clé étrangère par défaut: on les
    # active pour garder la même intégrité référentielle qu'en production
    # PostgreSQL (utile pour les cascades et les UniqueConstraint composites).
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db():
    """Dépendance FastAPI: fournit une session DB et la ferme proprement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema_compatibility() -> None:
    """Ajoute les colonnes introduites par les versions MVP sans détruire les données existantes."""
    if not is_sqlite:
        return
    additions = {
        "evaluation_results": {
            "validated_by_id": "INTEGER REFERENCES users(id)"
        },
        "schools": {
            "phone_secondary": "VARCHAR(50)",
            "official_stamp_path": "VARCHAR(500)",
            "ministry_name": "VARCHAR(255) DEFAULT 'Ministère de l’Éducation de Base' NOT NULL",
        }
    }
    with engine.begin() as conn:
        for table, columns in additions.items():
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
            for name, definition in columns.items():
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
