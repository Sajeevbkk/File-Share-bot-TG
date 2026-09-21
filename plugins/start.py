#(©)CodeXBotz

import os
import html
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT, START_PIC, AUTO_DELETE_TIME, AUTO_DELETE_MSG, JOIN_REQUEST_ENABLE, FORCE_SUB_CHANNEL, UNAUTHORIZED_TEXT, LOG_FILE_NAME, LOGGER
from helper_func import subscribed, decode, get_messages, delete_file, get_readable_time, track_session_message, get_session_user_messages, clear_session_user_messages
from database.database import add_user, del_user, full_userbase, present_user, get_user

logger = LOGGER(__name__)

@Bot.on_message(filters.private, group=-1)
async def track_incoming_session_messages(client: Bot, message: Message):
    if message.chat and message.chat.id and message.id:
        track_session_message(message.chat.id, message.id)

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    logger.info(f"Received /start command from user {user_id} ({first_name})")
    
    name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or None
    username = message.from_user.username
    try:
        await add_user(user_id, name=name, username=username)
    except Exception:
        pass
    text = message.text or ""
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except Exception:
            return
        try:
            string = await decode(base64_string)
        except Exception:
            await message.reply_text("Invalid link..!", quote=True)
            return
        argument = string.split("-")
        ids = []
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
            except Exception:
                return
            if start <= end:
                ids = list(range(start, end + 1))
            else:
                ids = []
                i = start
                while True:
                    ids.append(i)
                    i -= 1
                    if i < end:
                        break
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except Exception:
                return
        else:
            return

        if not ids:
            return

        temp_msg = await message.reply("Please wait...")
        try:
            messages = await get_messages(client, ids)
        except Exception:
            await message.reply_text("Something went wrong..!")
            return
        try:
            await temp_msg.delete()
        except Exception:
            pass

        track_msgs = []

        for msg in messages:
            if not msg:
                continue

            if bool(CUSTOM_CAPTION) and bool(getattr(msg, 'document', None)):
                try:
                    caption = CUSTOM_CAPTION.format(
                        previouscaption="" if not msg.caption else msg.caption.html,
                        filename=msg.document.file_name or ""
                    )
                except Exception:
                    caption = "" if not msg.caption else msg.caption.html
            else:
                caption = "" if not msg.caption else msg.caption.html

            if DISABLE_CHANNEL_BUTTON:
                reply_markup = msg.reply_markup
            else:
                reply_markup = None

            if AUTO_DELETE_TIME and AUTO_DELETE_TIME > 0:
                try:
                    copied_msg_for_deletion = await msg.copy(
                        chat_id=message.from_user.id,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup,
                        protect_content=PROTECT_CONTENT
                    )
                    if copied_msg_for_deletion:
                        track_msgs.append(copied_msg_for_deletion)
                except FloodWait as e:
                    wait_time = getattr(e, 'value', getattr(e, 'x', 1))
                    await asyncio.sleep(wait_time)
                    try:
                        copied_msg_for_deletion = await msg.copy(
                            chat_id=message.from_user.id,
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                            protect_content=PROTECT_CONTENT
                        )
                        if copied_msg_for_deletion:
                            track_msgs.append(copied_msg_for_deletion)
                    except Exception as err:
                        logger.error(f"Failed to copy message after retry: {err}")
                except Exception as e:
                    logger.error(f"Error copying message: {e}")
            else:
                try:
                    await msg.copy(
                        chat_id=message.from_user.id,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup,
                        protect_content=PROTECT_CONTENT
                    )
                    await asyncio.sleep(0.5)
                except FloodWait as e:
                    wait_time = getattr(e, 'value', getattr(e, 'x', 1))
                    await asyncio.sleep(wait_time)
                    try:
                        await msg.copy(
                            chat_id=message.from_user.id,
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                            protect_content=PROTECT_CONTENT
                        )
                    except Exception:
                        pass
                except Exception:
                    pass

        if track_msgs:
            try:
                delete_data = await client.send_message(
                    chat_id=message.from_user.id,
                    text=AUTO_DELETE_MSG.format(time=get_readable_time(AUTO_DELETE_TIME))
                )
                asyncio.create_task(delete_file(track_msgs, client, delete_data))
            except Exception as e:
                logger.error(f"Error scheduling auto-deletion: {e}")
        return
    else:
        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("😊 About Me", callback_data = "about"),
                    InlineKeyboardButton("🔒 Close", callback_data = "close")
                ]
            ]
        )
        first = message.from_user.first_name or ""
        last = message.from_user.last_name or ""
        username = None if not message.from_user.username else '@' + message.from_user.username
        mention = message.from_user.mention
        uid = message.from_user.id

        try:
            start_text = START_MSG.format(
                first=first,
                last=last,
                username=username,
                mention=mention,
                id=uid
            )
        except Exception:
            start_text = START_MSG

        if START_PIC:
            try:
                await message.reply_photo(
                    photo=START_PIC,
                    caption=start_text,
                    reply_markup=reply_markup,
                    quote=True
                )
            except Exception:
                await message.reply_text(
                    text=start_text,
                    reply_markup=reply_markup,
                    disable_web_page_preview=True,
                    quote=True
                )
        else:
            await message.reply_text(
                text=start_text,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                quote=True
            )
        return


#=====================================================================================##

WAIT_MSG = """"<b>Processing ...</b>"""

REPLY_ERROR = """<code>Use this command as a replay to any telegram message with out any spaces.</code>"""

#=====================================================================================##



@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    admin_id = message.from_user.id if message.from_user else "Unknown"
    admin_name = message.from_user.first_name or "Admin" if message.from_user else "Admin"
    logger.info(f"Admin {admin_id} ({admin_name}) used /users command")
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await full_userbase()
    
    if not users:
        await msg.edit("0 users are using this bot")
        return

    # Take only the last 25 users
    last_users = users[-25:]
    
    formatted = []
    for u in last_users:
        if isinstance(u, (tuple, list)):
            uid = u[0]
            uname = u[1] if len(u) > 1 else None
        elif isinstance(u, dict):
            uid = u.get('_id')
            uname = u.get('name')
        else:
            uid = u
            uname = None

        display_name = html.escape(uname) if uname else "User"
        formatted.append(f"<a href='tg://user?id={uid}'>{display_name}</a>  - <code>{uid}</code>")

    users_text = "\n".join(formatted)
    
    await msg.edit(f"{len(users)} users are using this bot\n\nLast 25 users:\n{users_text}")


@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    admin_id = message.from_user.id if message.from_user else "Unknown"
    admin_name = message.from_user.first_name or "Admin" if message.from_user else "Admin"
    logger.info(f"Admin {admin_id} ({admin_name}) used /broadcast command")
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        
        pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
        for u in query:
            chat_id = u[0] if isinstance(u, (tuple, list)) else (u.get('_id') if isinstance(u, dict) else u)
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                wait_time = getattr(e, 'value', getattr(e, 'x', 1))
                await asyncio.sleep(wait_time)
                try:
                    await broadcast_msg.copy(chat_id)
                    successful += 1
                except Exception:
                    unsuccessful += 1
            except UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except Exception:
                unsuccessful += 1
            total += 1
        
        status = f"""<b><u>Broadcast Completed</u>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code></b>"""
        
        return await pls_wait.edit(status)

    else:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        try:
            await msg.delete()
        except Exception:
            pass


@Bot.on_message(filters.command('log') & filters.private & filters.user(ADMINS))
async def show_log(client: Bot, message: Message):
    admin_id = message.from_user.id if message.from_user else "Unknown"
    admin_name = message.from_user.first_name or "Admin" if message.from_user else "Admin"
    logger.info(f"Admin {admin_id} ({admin_name}) used /log command")
    if os.path.exists(LOG_FILE_NAME):
        try:
            await message.reply_document(
                document=LOG_FILE_NAME,
                caption="Here is the log file.",
                quote=True
            )
        except Exception as e:
            logger.error(f"Failed to send log file: {e}")
            await message.reply_text(f"Failed to send log file: {e}", quote=True)
    else:
        await message.reply_text("Log file not found.", quote=True)

@Bot.on_message(filters.command(['clearlog', 'clearlogs', 'clear_log']) & filters.private & filters.user(ADMINS))
async def clear_log(client: Bot, message: Message):
    admin_id = message.from_user.id if message.from_user else "Unknown"
    admin_name = message.from_user.first_name or "Admin" if message.from_user else "Admin"
    cmd_name = message.command[0] if message.command else "clearlog"
    try:
        if os.path.exists(LOG_FILE_NAME):
            with open(LOG_FILE_NAME, "w") as f:
                f.truncate(0)
        else:
            with open(LOG_FILE_NAME, "w") as f:
                pass

        # Also clean up any rotated log backups (e.g. filesharingbot.txt.1, .2, etc.)
        dir_name = os.path.dirname(LOG_FILE_NAME) or "."
        base_name = os.path.basename(LOG_FILE_NAME)
        for fname in os.listdir(dir_name):
            if fname.startswith(base_name + "."):
                try:
                    os.remove(os.path.join(dir_name, fname))
                except Exception:
                    pass

        logger.info(f"Admin {admin_id} ({admin_name}) used /{cmd_name} to clear log file")
        await message.reply_text("✅ <b>Log file cleared successfully! Started a fresh log.</b>", quote=True)
    except Exception as e:
        logger.error(f"Failed to clear log file: {e}")
        await message.reply_text(f"❌ <b>Failed to clear log file:</b> <code>{e}</code>", quote=True)

@Bot.on_message(filters.command(['clearchats', 'clearchat', 'clear_chats', 'clear_chat']) & filters.private & filters.user(ADMINS))
async def clear_chats_command(client: Bot, message: Message):
    admin_id = message.from_user.id if message.from_user else "Unknown"
    admin_name = message.from_user.first_name or "Admin" if message.from_user else "Admin"
    cmd_name = message.command[0] if message.command else "clearchats"
    logger.info(f"Admin {admin_id} ({admin_name}) used /{cmd_name} command")

    session_data = get_session_user_messages()
    targets = {uid: msgs for uid, msgs in session_data.items() if msgs}

    if not targets:
        await message.reply_text("ℹ️ No session messages found with users to clear.", quote=True)
        return

    total_msgs_count = sum(len(msgs) for msgs in targets.values())
    status_msg = await message.reply_text(
        f"<i>Clearing {total_msgs_count} messages across {len(targets)} user chat(s)...</i>",
        quote=True
    )

    deleted_count = 0
    users_cleared = 0

    for u_id, msg_ids in targets.items():
        msg_id_list = list(msg_ids)
        if not msg_id_list:
            continue

        user_deleted = 0
        for i in range(0, len(msg_id_list), 100):
            chunk = msg_id_list[i:i + 100]
            try:
                del_res = await client.delete_messages(chat_id=u_id, message_ids=chunk, revoke=True)
                user_deleted += len(chunk) if del_res is None else (del_res if isinstance(del_res, int) and del_res > 0 else len(chunk))
            except FloodWait as e:
                wait_time = getattr(e, 'value', getattr(e, 'x', 1))
                await asyncio.sleep(wait_time)
                try:
                    del_res = await client.delete_messages(chat_id=u_id, message_ids=chunk, revoke=True)
                    user_deleted += len(chunk) if del_res is None else (del_res if isinstance(del_res, int) and del_res > 0 else len(chunk))
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Failed to delete session messages for user {u_id}: {e}")

        if user_deleted > 0:
            deleted_count += user_deleted
            users_cleared += 1

    clear_session_user_messages()
    logger.info(f"Admin {admin_id} ({admin_name}) cleared {deleted_count} messages across {users_cleared} user chat(s)")

    await status_msg.edit_text(
        f"✅ <b>Chats cleared successfully!</b>\n\n"
        f"• <b>Users affected:</b> <code>{users_cleared}</code>\n"
        f"• <b>Messages deleted:</b> <code>{deleted_count}</code>"
    )
