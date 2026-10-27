"""MongoDB Extension for CineBook Big-Data & Analytics Layer.

Provides lazy connection initialization, connection pooling, and graceful degradation
if MongoDB is unavailable (so transactional SQL bookings never break).
"""

import logging
from typing import Optional
from flask import Flask, current_app
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError, ConnectionFailure

logger = logging.getLogger(__name__)


class MongoManager:
    """Manages MongoDB connections with lazy initialization and connection pooling."""

    def __init__(self, app: Optional[Flask] = None):
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._custom_db: Optional[Database] = None
        self._is_available: Optional[bool] = None
        self._uri: Optional[str] = None
        self._db_name: Optional[str] = None
        self._server_timeout_ms: int = 1000
        self._connect_timeout_ms: int = 1000
        self._max_pool_size: int = 50
        self._min_pool_size: int = 5

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Register extension with Flask app configuration."""
        self._uri = app.config.get("MONGO_URI", "mongodb://localhost:27017")
        self._db_name = app.config.get("MONGO_DB_NAME", "cinebook_analytics")
        self._server_timeout_ms = int(app.config.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", 1000))
        self._connect_timeout_ms = int(app.config.get("MONGO_CONNECT_TIMEOUT_MS", 1000))
        self._max_pool_size = int(app.config.get("MONGO_MAX_POOL_SIZE", 50))
        self._min_pool_size = int(app.config.get("MONGO_MIN_POOL_SIZE", 5))

        # Store extension instance in app.extensions
        if not hasattr(app, "extensions"):
            app.extensions = {}
        app.extensions["mongo"] = self

    def _ensure_connected(self) -> bool:
        """Attempt to lazily connect to MongoDB if not already initialized."""
        if self._custom_db is not None:
            return True

        if self._client is not None and self._is_available:
            return True

        if not self._uri:
            # Try loading from current_app if available
            try:
                if current_app:
                    self.init_app(current_app._get_current_object())
            except RuntimeError:
                pass

        uri = self._uri or "mongodb://localhost:27017"
        db_name = self._db_name or "cinebook_analytics"

        try:
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=self._server_timeout_ms,
                connectTimeoutMS=self._connect_timeout_ms,
                maxPoolSize=self._max_pool_size,
                minPoolSize=self._min_pool_size,
                retryWrites=True,
            )
            # Lightweight ping command to verify availability
            client.admin.command("ping")
            self._client = client
            self._db = client[db_name]
            self._is_available = True
            logger.info("MongoDB connected successfully to '%s' (DB: %s)", uri.split("@")[-1], db_name)
            return True
        except (ServerSelectionTimeoutError, ConnectionFailure, PyMongoError) as exc:
            self._client = None
            self._db = None
            self._is_available = False
            logger.warning(
                "MongoDB is unavailable (%s). Analytics layer running in degraded mode; booking features remain fully operational.",
                exc
            )
            return False
        except Exception as exc:
            self._client = None
            self._db = None
            self._is_available = False
            logger.warning("Unexpected error connecting to MongoDB: %s", exc)
            return False

    def is_available(self) -> bool:
        """Check whether MongoDB is currently reachable."""
        if self._custom_db is not None:
            return True
        return self._ensure_connected()

    def get_client(self) -> Optional[MongoClient]:
        """Return the active MongoClient instance, or None if unavailable."""
        if self._ensure_connected():
            return self._client
        return None

    def get_db(self) -> Optional[Database]:
        """Return the active MongoDB Database instance, or None if unavailable."""
        if self._custom_db is not None:
            return self._custom_db
        if self._ensure_connected():
            return self._db
        return None

    def set_db(self, custom_db: Optional[Database]) -> None:
        """Override database instance (used for testing and mongomock injection)."""
        self._custom_db = custom_db
        if custom_db is not None:
            self._is_available = True

    def reset(self) -> None:
        """Reset connection state (useful between tests)."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None
        self._db = None
        self._custom_db = None
        self._is_available = None


mongo = MongoManager()
