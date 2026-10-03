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
banned_user_data = database['banned_users']

BANNED_USERS_CACHE = set()

async def load_banned_users_cache():
    global BANNED_USERS_CACHE
    try:
        banned_docs = banned_user_data.find({}, {'_id': 1})
        BANNED_USERS_CACHE = set(doc['_id'] for doc in banned_docs)
    except Exception as e:
        print(f"Error loading banned users cache: {e}")
    return BANNED_USERS_CACHE

async def is_user_banned(user_id: int) -> bool:
    if user_id in BANNED_USERS_CACHE:
        return True
    found = banned_user_data.find_one({'_id': user_id})
    if found:
        BANNED_USERS_CACHE.add(user_id)
        return True
    return False

async def ban_user(user_id: int, reason: str = None, banned_by: int = None, name: str = None, username: str = None):
    data = {}
    if reason is not None:
        data['reason'] = reason
    if banned_by is not None:
        data['banned_by'] = banned_by
    if name is not None:
        data['name'] = name
    if username is not None:
        data['username'] = username
    if data:
        banned_user_data.update_one({'_id': user_id}, {'$set': data}, upsert=True)
    else:
        banned_user_data.update_one({'_id': user_id}, {'$setOnInsert': {'_id': user_id}}, upsert=True)
    BANNED_USERS_CACHE.add(user_id)

async def unban_user(user_id: int) -> bool:
    if isinstance(user_id, (tuple, list)):
        user_id = user_id[0]
    elif isinstance(user_id, dict):
        user_id = user_id.get('_id')
    user_id = int(user_id)
    res = banned_user_data.delete_one({'_id': user_id})
    BANNED_USERS_CACHE.discard(user_id)
    return res.deleted_count > 0

async def get_banned_user(user_id: int):
    return banned_user_data.find_one({'_id': user_id})

async def full_banned_users():
    return list(banned_user_data.find())

async def full_banned_user_ids():
    return [doc['_id'] for doc in banned_user_data.find({}, {'_id': 1})]

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
        user_ids.append((doc['_id'], doc.get('name')))
        
    return user_ids

async def full_user_ids():
    user_docs = user_data.find()
    return [doc['_id'] for doc in user_docs]

async def del_user(user_id):
    if isinstance(user_id, (tuple, list)):
        user_id = user_id[0]
    elif isinstance(user_id, dict):
        user_id = user_id.get('_id')
    user_data.delete_one({'_id': int(user_id)})
    return
