"""
mongodb.py
==========
Async MongoDB client connection manager using Motor (Phase 7).

Manages database client lifecycle, startup/shutdown hooks, and collection accessors.
Configuration is validated against app.config settings (never hardcoded).

Author : AI Code Review Bot — Phase 7 (Stage 7.2)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

logger = logging.getLogger(__name__)


class MongoDBManager:
    """Singleton manager for AsyncIOMotorClient lifecycle."""

    def __init__(self) -> None:
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None

    @property
    def is_connected(self) -> bool:
        """True if the MongoDB client is active."""
        return self._client is not None

    async def connect(self, uri: Optional[str] = None, db_name: Optional[str] = None) -> None:
        """Initialize Motor client and connect to MongoDB.

        Args:
            uri: Optional override URI (defaults to settings.mongodb_uri).
            db_name: Optional override database name (defaults to settings.mongodb_database).
        """
        target_uri = uri if uri is not None else settings.mongodb_uri
        target_db_name = db_name if db_name is not None else settings.mongodb_database

        if not target_uri or not target_uri.strip():
            raise ValueError("MongoDB URI must not be empty.")
        if not target_db_name or not target_db_name.strip():
            raise ValueError("MongoDB database name must not be empty.")

        if self._client is not None:
            logger.debug("MongoDB client is already connected.")
            return

        logger.info(
            "Connecting to MongoDB — db_name=%s (URI hidden for security)",
            target_db_name,
        )

        try:
            self._client = AsyncIOMotorClient(
                target_uri,
                tz_aware=True,
                serverSelectionTimeoutMS=5000,
            )
            self._db = self._client[target_db_name]
            logger.info("MongoDB client connected successfully.")
        except Exception as exc:
            logger.error("Failed to connect to MongoDB: %s", exc)
            self.close()
            raise

    def close(self) -> None:
        """Close the MongoDB connection gracefully."""
        if self._client is not None:
            logger.info("Closing MongoDB client connection...")
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB client connection closed.")

    def get_database(self) -> AsyncIOMotorDatabase:
        """Return the active AsyncIOMotorDatabase instance.

        Raises:
            RuntimeError: If connect() has not been called or database is disconnected.
        """
        if self._db is None:
            raise RuntimeError(
                "MongoDB is not connected. Call connect_to_mongo() during application startup."
            )
        return self._db

    def get_collection(self, collection_name: str) -> Any:
        """Return a named collection from the active database."""
        db = self.get_database()
        return db[collection_name]


# Global singleton instance
_mongo_manager = MongoDBManager()


def get_mongo_manager() -> MongoDBManager:
    """Return global MongoDBManager instance."""
    return _mongo_manager


async def connect_to_mongo(uri: Optional[str] = None, db_name: Optional[str] = None) -> None:
    """FastAPI startup hook to connect MongoDB."""
    await _mongo_manager.connect(uri=uri, db_name=db_name)


def close_mongo_connection() -> None:
    """FastAPI shutdown hook to close MongoDB connection."""
    _mongo_manager.close()


def get_database() -> AsyncIOMotorDatabase:
    """FastAPI dependency / helper for accessing the active database."""
    return _mongo_manager.get_database()
