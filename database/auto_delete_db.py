import logging
from datetime import datetime, timedelta
from database.mongo import create_motor_client, retry_mongo_operation
from info import DATABASE_URI, DATABASE_NAME

logger = logging.getLogger(__name__)

client = create_motor_client(DATABASE_URI)
db = client[DATABASE_NAME]
auto_delete_col = db['auto_delete_queue']


async def ensure_auto_delete_indexes():
    """Create indexes for efficient querying of expired messages."""
    await retry_mongo_operation(
        "auto-delete index initialization",
        lambda: auto_delete_col.create_index([('delete_at', 1)]),
    )
    logger.info("Auto-delete indexes ensured.")


async def schedule_auto_delete(chat_id, message_id, delay_seconds=18000):
    """
    Schedule a message for auto-deletion after delay_seconds (default 5 hours).
    Saves the record to MongoDB so it survives bot restarts.
    """
    delete_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
    await retry_mongo_operation(
        "scheduling an auto-delete entry",
        lambda: auto_delete_col.update_one(
            {'chat_id': chat_id, 'message_id': message_id},
            {
                '$set': {'delete_at': delete_at},
                '$setOnInsert': {'created_at': datetime.utcnow()},
            },
            upsert=True,
        ),
    )
    logger.info(f"Scheduled auto-delete for msg {message_id} in chat {chat_id} at {delete_at}")


async def get_expired_messages():
    """Find all messages whose delete_at time has passed."""
    now = datetime.utcnow()

    async def load_expired_messages():
        cursor = auto_delete_col.find({'delete_at': {'$lte': now}})
        return await cursor.to_list(length=100)

    return await retry_mongo_operation(
        "loading expired auto-delete messages",
        load_expired_messages,
    )


async def remove_entry(entry_id):
    """Remove a processed entry from the auto-delete queue."""
    await retry_mongo_operation(
        "removing an auto-delete entry",
        lambda: auto_delete_col.delete_one({'_id': entry_id}),
    )
