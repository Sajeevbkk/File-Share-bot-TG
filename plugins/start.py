#(©)CodeXBotz

import os
import html
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import (
    ADMINS,
    OWNER_ID,
    START_MSG,
    FORCE_MSG,
    FORCE_SUB_CHANNEL,
    CUSTOM_CAPTION,
    DISABLE_CHANNEL_BUTTON,
    PROTECT_CONTENT,
    START_PIC,
    AUTO_DELETE_TIME,
    AUTO_DELETE_MSG,
    LOG_FILE_NAME,
    LOGGER
)
from helper_func import (
    subscribed,
    not_banned,
    decode,
    get_messages,
    delete_file,
    get_readable_time,
    track_session_message,
    get_session_user_messages,
    clear_session_user_messages,
    get_channel_post_link
)
from database.database import (
    add_user,
    del_user,
    full_userbase,
    get_user,
    is_user_banned,
    ban_user,
    unban_user,
    full_banned_users
)

logger = LOGGER(__name__)

@Bot.on_message(filters.private, group=-2)
async def check_banned_user_msg(client: Bot, message: Message):
    if message.from_user and await is_user_banned(message.from_user.id):
        message.stop_propagation()

@Bot.on_callback_query(group=-2)
async def check_banned_user_cb(client: Bot, query: CallbackQuery):
    if query.from_user and await is_user_banned(query.from_user.id):
        query.stop_propagation()

@Bot.on_message(filters.private & not_banned, group=-1)
async def track_incoming_session_messages(client: Bot, message: Message):
    if message.chat and message.chat.id and message.id:
        track_session_message(message.chat.id, message.id)

@Bot.on_message(filters.command('start') & filters.private & subscribed & not_banned)
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

        if not messages:
            await message.reply_text("File not found or message was deleted from DB Channel..!")
            return

        track_msgs = []
        file_entries = []

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

            copied_channel_msg = None
            try:
                copied_channel_msg = await msg.copy(
                    chat_id=FORCE_SUB_CHANNEL,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT
                )
            except FloodWait as e:
                wait_time = getattr(e, 'value', getattr(e, 'x', 1))
                await asyncio.sleep(wait_time)
                try:
                    copied_channel_msg = await msg.copy(
                        chat_id=FORCE_SUB_CHANNEL,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup,
                        protect_content=PROTECT_CONTENT
                    )
                except Exception as err:
                    logger.error(f"Failed to copy message to force sub channel after retry: {err}")
            except Exception as e:
                logger.error(f"Error copying message to force sub channel: {e}")

            if not copied_channel_msg:
                continue

            track_msgs.append(copied_channel_msg)
            post_link = copied_channel_msg.link
            if not post_link:
                fsub_uname = getattr(client, "force_sub_chat", None) and client.force_sub_chat.username
                post_link = get_channel_post_link(FORCE_SUB_CHANNEL, copied_channel_msg.id, username=fsub_uname)

            file_name = None
            if getattr(msg, 'document', None):
                file_name = msg.document.file_name
            elif getattr(msg, 'video', None):
                file_name = msg.video.file_name
            elif getattr(msg, 'audio', None):
                file_name = msg.audio.file_name

            file_entries.append({
                'name': file_name,
                'link': post_link,
                'msg': copied_channel_msg
            })

        if not file_entries:
            await message.reply_text("Failed to process requested file(s). Please try again later.")
            return

        private_link_messages = []
        if len(file_entries) == 1:
            entry = file_entries[0]
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("📁 Open File in Channel", url=entry['link'])]])
            name_text = f"<b>File:</b> <code>{html.escape(entry['name'])}</code>\n\n" if entry['name'] else ""
            link_text = (
                f"✅ <b>Your file is ready!</b>\n\n"
                f"{name_text}"
                f"🔗 <b>Link:</b> <a href='{entry['link']}'>{entry['link']}</a>\n\n"
                f"<i>Click the button below to view and download it in the channel.</i>"
            )
            sent_link_msg = await client.send_message(
                chat_id=message.from_user.id,
                text=link_text,
                reply_markup=btn,
                disable_web_page_preview=True
            )
            private_link_messages.append(sent_link_msg)
        else:
            buttons = []
            links_formatted = []
            for idx, entry in enumerate(file_entries, start=1):
                display_name = entry['name'] or f"File {idx}"
                links_formatted.append(f"{idx}. <a href='{entry['link']}'>{html.escape(display_name)}</a>")
                buttons.append([InlineKeyboardButton(f"📁 {display_name[:28]}", url=entry['link'])])

            batch_text = (
                f"✅ <b>Your batch files are ready!</b>\n\n"
                f"<b>Total Files:</b> <code>{len(file_entries)}</code>\n\n"
                + "\n".join(links_formatted) +
                f"\n\n<i>Click below to view the files in the channel.</i>"
            )
            markup = InlineKeyboardMarkup(buttons) if len(buttons) <= 10 else None
            sent_link_msg = await client.send_message(
                chat_id=message.from_user.id,
                text=batch_text,
                reply_markup=markup,
                disable_web_page_preview=True
            )
            private_link_messages.append(sent_link_msg)

        track_msgs.extend(private_link_messages)

        if AUTO_DELETE_TIME and AUTO_DELETE_TIME > 0:
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

@Bot.on_message(filters.command('start') & filters.private & not_banned)
async def not_joined(client: Client, message: Message):
    if not message.from_user:
        return
    buttons = [
        [
            InlineKeyboardButton(
                "📢 Join Channel",
                url=client.invitelink
            )
        ]
    ]
    if len(message.command) > 1:
        buttons.append(
            [
                InlineKeyboardButton(
                    "🔄 Try Again",
                    url=f"https://t.me/{client.username}?start={message.command[1]}"
                )
            ]
        )

    first = message.from_user.first_name or ""
    last = message.from_user.last_name or ""
    username = None if not message.from_user.username else '@' + message.from_user.username
    mention = message.from_user.mention
    uid = message.from_user.id

    try:
        force_text = FORCE_MSG.format(
            first=first,
            last=last,
            username=username,
            mention=mention,
            id=uid
        )
    except Exception:
        force_text = FORCE_MSG

    await message.reply_text(
        text=force_text,
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True,
        disable_web_page_preview=True
    )


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
                user_deleted += len(chunk) if (del_res is None or isinstance(del_res, bool)) else (del_res if isinstance(del_res, int) and del_res > 0 else len(chunk))
            except FloodWait as e:
                wait_time = getattr(e, 'value', getattr(e, 'x', 1))
                await asyncio.sleep(wait_time)
                try:
                    del_res = await client.delete_messages(chat_id=u_id, message_ids=chunk, revoke=True)
                    user_deleted += len(chunk) if (del_res is None or isinstance(del_res, bool)) else (del_res if isinstance(del_res, int) and del_res > 0 else len(chunk))
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

@Bot.on_message(filters.command('ban') & filters.private & filters.user(ADMINS))
async def ban_command(client: Bot, message: Message):
    admin_id = message.from_user.id if message.from_user else "Unknown"
    admin_name = message.from_user.first_name or "Admin" if message.from_user else "Admin"
    logger.info(f"Admin {admin_id} ({admin_name}) used /ban command: {message.text}")

    target_user_id = None
    reason = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user or message.reply_to_message.forward_from
        if target_user:
            target_user_id = target_user.id
        if len(message.command) > 1:
            reason = " ".join(message.command[1:])
    elif len(message.command) > 1:
        try:
            target_user_id = int(message.command[1])
        except ValueError:
            await message.reply_text("❌ <b>Invalid user ID.</b> User ID must be an integer.", quote=True)
            return
        if len(message.command) > 2:
            reason = " ".join(message.command[2:])

    if not target_user_id:
        usage = (
            "<b>Usage:</b>\n"
            "• <code>/ban [user_id] [optional reason]</code>\n"
            "• Reply to a user's message with <code>/ban [optional reason]</code>"
        )
        await message.reply_text(usage, quote=True)
        return

    if target_user_id in ADMINS or target_user_id == OWNER_ID:
        await message.reply_text("❌ <b>You cannot ban an admin or the owner!</b>", quote=True)
        return

    target_name = None
    target_username = None
    try:
        user_obj = await client.get_users(target_user_id)
        if user_obj:
            target_name = f"{user_obj.first_name or ''} {user_obj.last_name or ''}".strip() or None
            target_username = user_obj.username
    except Exception:
        pass

    if not target_name:
        try:
            doc = await get_user(target_user_id)
            if doc:
                target_name = doc.get('name')
                target_username = doc.get('username')
        except Exception:
            pass

    await ban_user(
        user_id=target_user_id,
        reason=reason,
        banned_by=message.from_user.id if message.from_user else None,
        name=target_name,
        username=target_username
    )

    uname_str = f" (@{target_username})" if target_username else ""
    display_name = f"<a href='tg://user?id={target_user_id}'>{html.escape(target_name)}</a>" if target_name else f"<code>{target_user_id}</code>"
    reason_str = html.escape(reason) if reason else "None specified"

    await message.reply_text(
        f"✅ <b>User has been banned successfully!</b>\n\n"
        f"• <b>User:</b> {display_name}{uname_str}\n"
        f"• <b>ID:</b> <code>{target_user_id}</code>\n"
        f"• <b>Reason:</b> <code>{reason_str}</code>",
        quote=True
    )

@Bot.on_message(filters.command('unban') & filters.private & filters.user(ADMINS))
async def unban_command(client: Bot, message: Message):
    admin_id = message.from_user.id if message.from_user else "Unknown"
    admin_name = message.from_user.first_name or "Admin" if message.from_user else "Admin"
    logger.info(f"Admin {admin_id} ({admin_name}) used /unban command: {message.text}")

    target_user_id = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user or message.reply_to_message.forward_from
        if target_user:
            target_user_id = target_user.id
    elif len(message.command) > 1:
        try:
            target_user_id = int(message.command[1])
        except ValueError:
            await message.reply_text("❌ <b>Invalid user ID.</b> User ID must be an integer.", quote=True)
            return

    if not target_user_id:
        usage = (
            "<b>Usage:</b>\n"
            "• <code>/unban [user_id]</code>\n"
            "• Reply to a user's message with <code>/unban</code>"
        )
        await message.reply_text(usage, quote=True)
        return

    res = await unban_user(target_user_id)
    if res:
        await message.reply_text(
            f"✅ <b>User <code>{target_user_id}</code> has been unbanned successfully!</b>",
            quote=True
        )
    else:
        await message.reply_text(
            f"ℹ️ <b>User <code>{target_user_id}</code> was not in the ban list.</b>",
            quote=True
        )

@Bot.on_message(filters.command(['banned', 'banlist', 'bannedusers']) & filters.private & filters.user(ADMINS))
async def list_banned_command(client: Bot, message: Message):
    admin_id = message.from_user.id if message.from_user else "Unknown"
    admin_name = message.from_user.first_name or "Admin" if message.from_user else "Admin"
    logger.info(f"Admin {admin_id} ({admin_name}) used /banned command")

    banned_users = await full_banned_users()
    if not banned_users:
        await message.reply_text("ℹ️ <b>No users are currently banned.</b>", quote=True)
        return

    wait_msg = await message.reply_text("<i>Fetching banned users list...</i>", quote=True)

    formatted_users = []
    plain_users = []

    for idx, doc in enumerate(banned_users, start=1):
        uid = doc.get('_id')
        name = doc.get('name')
        username = doc.get('username')
        reason = doc.get('reason') or "No reason"

        uname_str = f" (@{username})" if username else ""
        if name:
            escaped_name = html.escape(name)
            html_line = f"• <a href='tg://user?id={uid}'>{escaped_name}</a>{uname_str} - <code>{uid}</code> (Reason: {html.escape(reason)})"
            plain_line = f"{idx}. {name}{uname_str} - ID: {uid} (Reason: {reason})"
        elif username:
            html_line = f"• <a href='tg://user?id={uid}'>@{username}</a> - <code>{uid}</code> (Reason: {html.escape(reason)})"
            plain_line = f"{idx}. @{username} - ID: {uid} (Reason: {reason})"
        else:
            html_line = f"• User - <code>{uid}</code> (Reason: {html.escape(reason)})"
            plain_line = f"{idx}. ID: {uid} (Reason: {reason})"

        formatted_users.append(html_line)
        plain_users.append(plain_line)

    text = f"<b>Total Banned Users:</b> <code>{len(banned_users)}</code>\n\n" + "\n".join(formatted_users)

    if len(text) > 4000:
        file_name = "banned_users.txt"
        try:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(f"Total Banned Users: {len(banned_users)}\n\n" + "\n".join(plain_users))
            await message.reply_document(
                document=file_name,
                caption=f"<b>Total Banned Users:</b> <code>{len(banned_users)}</code>",
                quote=True
            )
            try:
                await wait_msg.delete()
            except Exception:
                pass
        except Exception as e:
            try:
                await wait_msg.edit_text(f"Error generating banned users list file: {e}")
            except Exception:
                pass
        finally:
            if os.path.exists(file_name):
                try:
                    os.remove(file_name)
                except Exception:
                    pass
    else:
        try:
            await wait_msg.edit_text(text, disable_web_page_preview=True)
        except Exception:
            await message.reply_text(text, disable_web_page_preview=True, quote=True)
