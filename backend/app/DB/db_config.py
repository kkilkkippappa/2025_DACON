from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Callable, Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

Base = declarative_base()


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
    """Reusable DB configuration cached per table (database) name."""

    def __init__(self, table_name: str | None = None):
        self.table_name = table_name or os.getenv("DB_NAME", "sensor_data")

        self.database_url = _build_database_url(self.table_name)
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

        _dependency.__name__ = f"get_db_{self.table_name}"
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
def get_db_config(table_name: str | None = None) -> DBConfig:
    """Create (or fetch cached) DBConfig for the given table/database name."""
    return DBConfig(table_name=table_name)


default_db_config = get_db_config()
get_db = default_db_config.dependency()


def get_db_for_table(table_name: str) -> Callable[[], Generator[Session, None, None]]:
    """Return a dependency factory for the given table tag."""
    return get_db_config(table_name).dependency()


def session_scope(table_name: str | None = None):
    """Context manager factory that can be tagged per table."""
    config = get_db_config(table_name)
    return config.session_scope()
