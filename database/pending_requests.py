import hashlib
from datetime import datetime, timedelta

from pymongo import ReturnDocument

from database.mongo import create_motor_client
from info import DATABASE_NAME, DATABASE_URI, PENDING_REQUEST_TTL_HOURS


client = create_motor_client(DATABASE_URI)
collection = client[DATABASE_NAME]["pending_requests"]


def _now():
    # Motor/PyMongo stores UTC datetimes without timezone information by
    # default, so keep all comparisons consistently UTC-naive.
    return datetime.utcnow()


def request_token(user_id, request_id, mode):
    value = f"{int(user_id)}\0{mode}\0{request_id}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:20]


async def ensure_pending_request_indexes():
    await collection.create_index([("user_id", 1), ("status", 1), ("requested_at", 1)])
    await collection.create_index("expires_at", expireAfterSeconds=0)


async def save_pending_request(user_id, request_id, mode="checksub"):
    token = request_token(user_id, request_id, mode)
    now = _now()
    expires_at = now + timedelta(hours=PENDING_REQUEST_TTL_HOURS)
    document = {
        "user_id": int(user_id),
        "request_id": str(request_id),
        "mode": str(mode),
        "requested_at": now,
        "expires_at": expires_at,
        "status": "pending",
    }
    result = await collection.update_one(
        {"_id": token, "status": {"$ne": "delivering"}},
        {
            "$set": document,
            "$unset": {"delivered_at": "", "delivery_error": ""},
        },
    )
    if not result.matched_count:
        # Do not turn a currently delivering record back into pending. This is
        # the final guard against a double-click racing automatic delivery.
        await collection.update_one(
            {"_id": token},
            {"$setOnInsert": document},
            upsert=True,
        )
    return token


async def claim_pending_request(token, user_id=None):
    query = {
        "_id": token,
        "status": "pending",
        "expires_at": {"$gt": _now()},
    }
    if user_id is not None:
        query["user_id"] = int(user_id)
    return await collection.find_one_and_update(
        query,
        {"$set": {"status": "delivering", "delivery_started_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )


async def claim_next_pending_request(user_id):
    return await collection.find_one_and_update(
        {
            "user_id": int(user_id),
            "status": "pending",
            "expires_at": {"$gt": _now()},
        },
        {"$set": {"status": "delivering", "delivery_started_at": _now()}},
        sort=[("requested_at", 1)],
        return_document=ReturnDocument.AFTER,
    )


async def mark_pending_delivered(token):
    await collection.update_one(
        {"_id": token, "status": "delivering"},
        {"$set": {"status": "delivered", "delivered_at": _now()}},
    )


async def release_pending_request(token, error=None):
    update = {"status": "pending"}
    if error:
        update["delivery_error"] = str(error)[:500]
    await collection.update_one(
        {"_id": token, "status": "delivering"},
        {"$set": update, "$unset": {"delivery_started_at": ""}},
    )


async def expire_old_pending_requests():
    return await collection.update_many(
        {"status": "pending", "expires_at": {"$lte": _now()}},
        {"$set": {"status": "expired"}},
    )
