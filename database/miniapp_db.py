from datetime import datetime

from database.mongo import create_motor_client
from info import DATABASE_NAME, DATABASE_URI


client = create_motor_client(DATABASE_URI)
collection = client[DATABASE_NAME]["miniapp_users"]


async def ensure_miniapp_indexes():
    await collection.create_index("updated_at")


async def get_profile(user_id):
    profile = await collection.find_one({"_id": int(user_id)})
    return profile or {"_id": int(user_id), "favorites": [], "history": []}


async def add_favorite(user_id, movie_id):
    await collection.update_one(
        {"_id": int(user_id)},
        {
            "$addToSet": {"favorites": str(movie_id)},
            "$set": {"updated_at": datetime.utcnow()},
        },
        upsert=True,
    )


async def remove_favorite(user_id, movie_id):
    await collection.update_one(
        {"_id": int(user_id)},
        {
            "$pull": {"favorites": str(movie_id)},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )


async def add_history(user_id, movie_id):
    # Pull first so the most recent request appears once at the front.
    await collection.update_one(
        {"_id": int(user_id)},
        {"$pull": {"history": str(movie_id)}},
        upsert=True,
    )
    await collection.update_one(
        {"_id": int(user_id)},
        {
            "$push": {
                "history": {
                    "$each": [str(movie_id)],
                    "$position": 0,
                    "$slice": 30,
                }
            },
            "$set": {"updated_at": datetime.utcnow()},
        },
    )
