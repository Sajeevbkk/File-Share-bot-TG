from bot import Bot
from pyrogram.types import Message
from pyrogram import filters
from config import ADMINS, BOT_STATS_TEXT, USER_REPLY_TEXT, LOGGER
from datetime import datetime
from helper_func import get_readable_time

@Bot.on_message(filters.command('stats') & filters.user(ADMINS))
async def stats(bot: Bot, message: Message):
    now = datetime.now()
    delta = now - getattr(bot, 'uptime', now)
    time = get_readable_time(int(delta.total_seconds()))
    await message.reply(BOT_STATS_TEXT.format(uptime=time))

@Bot.on_message(filters.private & filters.incoming & ~filters.user(ADMINS) & ~filters.command(['start','users','broadcast','batch','genlink','stats','add','remove','special_users','specialusers','special','log']))
async def useless(_, message: Message):
    if not message.from_user:
        return
    if USER_REPLY_TEXT:
        try:
            await message.reply(USER_REPLY_TEXT)
        except Exception:
            pass
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name or "Unknown"
        text_content = message.text or message.caption or "<Media/Other>"
        LOGGER(__name__).info(f"Received message from user {user_id} ({first_name}): {text_content}")
    except Exception as e:
        LOGGER(__name__).error(f"Error logging message: {e}")
