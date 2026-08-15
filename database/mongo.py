import asyncio
import logging

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import (
    AutoReconnect,
    ConnectionFailure,
    NetworkTimeout,
    NotPrimaryError,
    ServerSelectionTimeoutError,
)


logger = logging.getLogger(__name__)

RETRYABLE_MONGO_ERRORS = (
    AutoReconnect,
    ConnectionFailure,
    NetworkTimeout,
    NotPrimaryError,
    ServerSelectionTimeoutError,
)

MONGO_CLIENT_OPTIONS = {
    "serverSelectionTimeoutMS": 30000,
    "connectTimeoutMS": 30000,
    "socketTimeoutMS": 30000,
}

_clients = {}


def create_motor_client(uri):
    if uri not in _clients:
        _clients[uri] = AsyncIOMotorClient(uri, **MONGO_CLIENT_OPTIONS)
    return _clients[uri]


async def retry_mongo_operation(operation_name, operation, retries=5):
    """Retry a read or idempotent MongoDB operation after transient failures."""
    if retries < 1:
        raise ValueError("retries must be at least 1")

    for attempt in range(1, retries + 1):
        try:
            return await operation()
        except RETRYABLE_MONGO_ERRORS as error:
            if attempt == retries:
                raise

            delay = min(2 ** (attempt - 1), 10)
            logger.warning(
                "MongoDB transient error during %s; retrying in %ss (%s/%s): %s",
                operation_name,
                delay,
                attempt,
                retries,
                error,
            )
            await asyncio.sleep(delay)
