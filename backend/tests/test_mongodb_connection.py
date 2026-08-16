"""
test_mongodb_connection.py
===========================
Unit tests for Stage 7.2 MongoDB Connection infrastructure.

Tests cover:
- MongoDBManager startup, database retrieval, and shutdown.
- Error handling when accessing uninitialized database.
- Configuration validation (rejecting empty URI/DB name).
- Mocked Motor client startup and shutdown lifecycle.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.db.mongodb import MongoDBManager


@pytest.mark.asyncio
async def test_mongo_manager_unconnected_raises_runtime_error():
    """Accessing get_database() before connect() raises RuntimeError."""
    manager = MongoDBManager()
    assert manager.is_connected is False
    with pytest.raises(RuntimeError, match="MongoDB is not connected"):
        manager.get_database()


@pytest.mark.asyncio
async def test_mongo_manager_invalid_config_raises_value_error():
    """Empty URI or DB name raises ValueError."""
    manager = MongoDBManager()

    with pytest.raises(ValueError, match="MongoDB URI must not be empty"):
        await manager.connect(uri="   ", db_name="test_db")

    with pytest.raises(ValueError, match="MongoDB database name must not be empty"):
        await manager.connect(uri="mongodb://localhost:27017", db_name="")


@pytest.mark.asyncio
async def test_mongo_manager_successful_connection_lifecycle():
    """Verify connect and close lifecycle with mocked AsyncIOMotorClient."""
    manager = MongoDBManager()

    with patch("app.db.mongodb.AsyncIOMotorClient") as MockClient:
        mock_client_instance = MagicMock()
        mock_db_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db_instance
        MockClient.return_value = mock_client_instance

        await manager.connect(uri="mongodb://localhost:27017", db_name="custom_review_db")

        assert manager.is_connected is True
        assert manager.get_database() is mock_db_instance
        assert manager.get_collection("reviews") == mock_db_instance["reviews"]

        manager.close()

        assert manager.is_connected is False
        mock_client_instance.close.assert_called_once()


@pytest.mark.asyncio
async def test_mongo_manager_reconnect_idempotent():
    """Subsequent connect() calls on already-connected manager are no-ops."""
    manager = MongoDBManager()

    with patch("app.db.mongodb.AsyncIOMotorClient") as MockClient:
        mock_client_instance = MagicMock()
        MockClient.return_value = mock_client_instance

        await manager.connect(uri="mongodb://localhost:27017", db_name="db1")
        await manager.connect(uri="mongodb://localhost:27017", db_name="db1")

        # MockClient should only be constructed once
        assert MockClient.call_count == 1

        manager.close()
