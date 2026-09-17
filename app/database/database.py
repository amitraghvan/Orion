"""SQLite database engine and session lifecycle manager."""

from __future__ import annotations

import threading
from pathlib import Path

from app.core.logging import get_logger
from app.core.paths import paths
from app.database.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

logger = get_logger("app.database.engine")


class DatabaseManager:
    """Manages embedded SQLite database connection and schema creation."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or paths.database_path
        self._engine = None
        self._session_factory = None
        self._lock = threading.Lock()

    def initialize(self) -> None:
        """Create SQLite engine, initialize schema tables, and configure session factory."""
        with self._lock:
            if self._engine is not None:
                return

            db_url = f"sqlite:///{self.db_path}"
            self._engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                echo=False,
            )
            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine,
            )

            # Create tables
            Base.metadata.create_all(bind=self._engine)
            logger.info("Local SQLite database initialized", path=str(self.db_path))

    def get_session(self) -> Session:
        """Acquire a thread-local SQLite session."""
        if self._session_factory is None:
            self.initialize()
        return self._session_factory()  # type: ignore[misc]


# Global database manager singleton
db_manager = DatabaseManager()
