#(©)CodeXBotz

import pymongo, os
from config import DB_URI, DB_NAME

try:
    import certifi
    ca = certifi.where()
except ImportError:
    ca = None

if ca:
    dbclient = pymongo.MongoClient(DB_URI, tlsCAFile=ca)
else:
    dbclient = pymongo.MongoClient(DB_URI)

database = dbclient[DB_NAME]
user_data = database['users']
special_user_data = database['special_users']

async def present_user(user_id : int):
    found = user_data.find_one({'_id': user_id})
    return bool(found)

async def add_user(user_id: int, name: str = None, username: str = None):
    data = {}
    if name is not None:
        data['name'] = name
    if username is not None:
        data['username'] = username
    if data:
        user_data.update_one({'_id': user_id}, {'$set': data}, upsert=True)
    else:
        user_data.update_one({'_id': user_id}, {'$setOnInsert': {'_id': user_id}}, upsert=True)
    return

async def get_user(user_id: int):
    return user_data.find_one({'_id': user_id})

async def full_userbase():
    user_docs = user_data.find()
    user_ids = []
    for doc in user_docs:
        user_ids.append(doc['_id'])
        
    return user_ids

async def del_user(user_id: int):
    user_data.delete_one({'_id': user_id})
    return

async def present_special_user(user_id : int):
    found = special_user_data.find_one({'_id': user_id})
    return bool(found)

async def add_special_user(user_id: int, name: str = None, username: str = None):
    data = {}
    if name is not None:
        data['name'] = name
    if username is not None:
        data['username'] = username
    if data:
        special_user_data.update_one({'_id': user_id}, {'$set': data}, upsert=True)
    else:
        special_user_data.update_one({'_id': user_id}, {'$setOnInsert': {'_id': user_id}}, upsert=True)
    return

async def get_special_user(user_id: int):
    return special_user_data.find_one({'_id': user_id})

async def del_special_user(user_id: int):
    special_user_data.delete_one({'_id': user_id})
    return

async def full_special_userbase():
    user_docs = special_user_data.find()
    user_ids = []
    for doc in user_docs:
        user_ids.append(doc['_id'])
    return user_ids

async def full_special_user_docs():
    user_docs = special_user_data.find()
    return list(user_docs)
