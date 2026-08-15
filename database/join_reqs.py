#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) @AlbertEinsteinTG

import logging

from database.mongo import create_motor_client
from info import JOIN_REQS_DB, REQ_CHANNEL


logger = logging.getLogger(__name__)

class JoinReqs:

    def __init__(self):
        if JOIN_REQS_DB and REQ_CHANNEL:
            self.client = create_motor_client(JOIN_REQS_DB)
            self.db = self.client["JoinReqs"]
            self.col = self.db[str(REQ_CHANNEL)]
        else:
            self.client = None
            self.db = None
            self.col = None

    def is_active(self):
        return self.client is not None and bool(REQ_CHANNEL)

    def isActive(self):
        return self.is_active()

    async def add_user(self, user_id, first_name, username, date):
        user_id = int(user_id)
        await self.col.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "first_name": first_name,
                    "username": username,
                    "date": date,
                }
            },
            upsert=True,
        )

    async def get_user(self, user_id):
        return await self.col.find_one({"user_id": int(user_id)})

    async def get_all_users(self):
        return await self.col.find().to_list(None)

    async def delete_user(self, user_id):
        await self.col.delete_one({"user_id": int(user_id)})

    async def delete_all_users(self):
        await self.col.delete_many({})

    async def get_all_users_count(self):
        return await self.col.count_documents({})


join_reqs = JoinReqs()
