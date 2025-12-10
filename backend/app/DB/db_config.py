from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Callable, Generator, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

Base = declarative_base()

DEFAULT_SCHEMA = os.getenv("DB_NAME", "sensor_data")
DEFAULT_TABLE = "sensor"


def _build_database_url(db_name: str) -> str:
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PW", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT")
    db_charset = os.getenv("CHARSET", "utf8mb4")

    if not db_port:
        if db_host.isdigit():
            db_port = db_host
            db_host = "localhost"
        else:
            db_port = "3306"

    return (
        f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        f"?charset={db_charset}"
    )


class DBConfig:
    """Reusable DB configuration keyed by schema/table pair."""

    def __init__(self, *, schema_name: str, table_name: str):
        if not schema_name:
            raise ValueError("schema_name must be provided")
        if not table_name:
            raise ValueError("table_name must be provided")

        self.schema_name = schema_name
        self.table_name = table_name

        self.database_url = _build_database_url(self.schema_name)
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
        self._session_factory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )

    def session(self) -> Session:
        return self._session_factory()

    def dependency(self) -> Callable[[], Generator[Session, None, None]]:
        def _dependency():
            db = self.session()
            try:
                yield db
            finally:
                db.close()

        _dependency.__name__ = f"get_db_{self.schema_name}_{self.table_name}"
        return _dependency

    def session_scope(self):
        @contextmanager
        def _scope():
            db = self.session()
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        return _scope()


@lru_cache(maxsize=None)
def get_db_config(schema_name: str, table_name: str) -> DBConfig:
    """Create (or fetch cached) DBConfig for the given schema/table pair."""
    return DBConfig(schema_name=schema_name, table_name=table_name)


default_db_config = get_db_config(DEFAULT_SCHEMA, DEFAULT_TABLE)
get_db = default_db_config.dependency()


def get_db_for_table(
    table_name: str,
    *,
    schema_name: Optional[str] = None,
) -> Callable[[], Generator[Session, None, None]]:
    """Return a dependency factory using the provided schema/table combination."""
    resolved_schema = schema_name or DEFAULT_SCHEMA
    return get_db_config(resolved_schema, table_name).dependency()


def session_scope(
    *,
    schema_name: Optional[str] = None,
    table_name: Optional[str] = None,
):
    """Context manager factory that can be tagged per schema/table."""
    resolved_schema = schema_name or DEFAULT_SCHEMA
    resolved_table = table_name or DEFAULT_TABLE
    config = get_db_config(resolved_schema, resolved_table)
    return config.session_scope()
