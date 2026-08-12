#(©)CodeXBotz

import os
import html
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT, START_PIC, AUTO_DELETE_TIME, AUTO_DELETE_MSG, JOIN_REQUEST_ENABLE, FORCE_SUB_CHANNEL, UNAUTHORIZED_TEXT
from helper_func import subscribed, decode, get_messages, delete_file
from database.database import add_user, del_user, full_userbase, present_user, get_user, present_special_user, add_special_user, del_special_user, full_special_userbase, get_special_user


@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or None
    username = message.from_user.username
    try:
        await add_user(id, name=name, username=username)
    except Exception:
        pass
    if await present_special_user(id):
        try:
            await add_special_user(id, name=name, username=username)
        except Exception:
            pass
    text = message.text
    if len(text)>7:
        if not (id in ADMINS or await present_special_user(id)):
            await message.reply_text(
                UNAUTHORIZED_TEXT,
                quote=True,
                disable_web_page_preview=True
            )
            return
        try:
            base64_string = text.split(" ", 1)[1]
        except:
            return
        string = await decode(base64_string)
        argument = string.split("-")
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
            except:
                return
            if start <= end:
                ids = range(start,end+1)
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
            except:
                return
        temp_msg = await message.reply("Please wait...")
        try:
            messages = await get_messages(client, ids)
        except:
            await message.reply_text("Something went wrong..!")
            return
        await temp_msg.delete()

        track_msgs = []

        for msg in messages:

            if bool(CUSTOM_CAPTION) & bool(msg.document):
                caption = CUSTOM_CAPTION.format(previouscaption = "" if not msg.caption else msg.caption.html, filename = msg.document.file_name)
            else:
                caption = "" if not msg.caption else msg.caption.html

            if DISABLE_CHANNEL_BUTTON:
                reply_markup = msg.reply_markup
            else:
                reply_markup = None

            if AUTO_DELETE_TIME and AUTO_DELETE_TIME > 0:

                try:
                    copied_msg_for_deletion = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    if copied_msg_for_deletion:
                        track_msgs.append(copied_msg_for_deletion)
                    else:
                        print("Failed to copy message, skipping.")

                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    copied_msg_for_deletion = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    if copied_msg_for_deletion:
                        track_msgs.append(copied_msg_for_deletion)
                    else:
                        print("Failed to copy message after retry, skipping.")

                except Exception as e:
                    print(f"Error copying message: {e}")
                    pass

            else:
                try:
                    await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    await asyncio.sleep(0.5)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                except:
                    pass

        if track_msgs:
            delete_data = await client.send_message(
                chat_id=message.from_user.id,
                text=AUTO_DELETE_MSG.format(time=AUTO_DELETE_TIME)
            )
            # Schedule the file deletion task after all messages have been copied
            asyncio.create_task(delete_file(track_msgs, client, delete_data))
        else:
            print("No messages to track for deletion.")

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
        if START_PIC:  # Check if START_PIC has a value
            await message.reply_photo(
                photo=START_PIC,
                caption=START_MSG.format(
                    first=message.from_user.first_name,
                    last=message.from_user.last_name,
                    username=None if not message.from_user.username else '@' + message.from_user.username,
                    mention=message.from_user.mention,
                    id=message.from_user.id
                ),
                reply_markup=reply_markup,
                quote=True
            )
        else:  # If START_PIC is empty, send only the text
            await message.reply_text(
                text=START_MSG.format(
                    first=message.from_user.first_name,
                    last=message.from_user.last_name,
                    username=None if not message.from_user.username else '@' + message.from_user.username,
                    mention=message.from_user.mention,
                    id=message.from_user.id
                ),
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                quote=True
            )
        return

    
#=====================================================================================##

WAIT_MSG = """"<b>Processing ...</b>"""

REPLY_ERROR = """<code>Use this command as a replay to any telegram message with out any spaces.</code>"""

#=====================================================================================##


@Bot.on_message(filters.command('start') & filters.private)
async def not_joined(client: Client, message: Message):
    id = message.from_user.id
    name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or None
    username = message.from_user.username
    try:
        await add_user(id, name=name, username=username)
    except Exception:
        pass

    if bool(JOIN_REQUEST_ENABLE):
        invite = await client.create_chat_invite_link(
            chat_id=FORCE_SUB_CHANNEL,
            creates_join_request=True
        )
        ButtonUrl = invite.invite_link
    else:
        ButtonUrl = client.invitelink

    buttons = [
        [
            InlineKeyboardButton(
                "Join Channel",
                url = ButtonUrl)
        ]
    ]

    try:
        buttons.append(
            [
                InlineKeyboardButton(
                    text = 'Try Again',
                    url = f"https://t.me/{client.username}?start={message.command[1]}"
                )
            ]
        )
    except IndexError:
        pass

    await message.reply(
        text = FORCE_MSG.format(
                first = message.from_user.first_name,
                last = message.from_user.last_name,
                username = None if not message.from_user.username else '@' + message.from_user.username,
                mention = message.from_user.mention,
                id = message.from_user.id
            ),
        reply_markup = InlineKeyboardMarkup(buttons),
        quote = True,
        disable_web_page_preview = True
    )

@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")

@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        
        pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except:
                unsuccessful += 1
                pass
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
        await msg.delete()


@Bot.on_message(filters.command('add') & filters.private & filters.user(ADMINS))
async def add_special_user_handler(client: Bot, message: Message):
    user_ids = []
    user_info_map = {}

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user or message.reply_to_message.forward_from
        if target_user:
            user_ids.append(target_user.id)
            full_name = f"{target_user.first_name or ''} {target_user.last_name or ''}".strip() or None
            user_info_map[target_user.id] = {
                'name': full_name,
                'username': target_user.username
            }

    if len(message.command) > 1:
        for arg in message.command[1:]:
            try:
                user_ids.append(int(arg))
            except ValueError:
                await message.reply_text(f"❌ Invalid user ID: <code>{arg}</code>. User ID must be an integer.", quote=True)
                return

    if not user_ids:
        msg_text = (
            "<b>Usage:</b>\n"
            "• <code>/add [user_id]</code> - Add user to special users list\n"
            "• <code>/add [id1] [id2] ...</code> - Add multiple users\n"
            "• Reply to a user's message with <code>/add</code>"
        )
        await message.reply_text(msg_text, quote=True)
        return

    user_ids = list(dict.fromkeys(user_ids))
    added = []
    already_present = []
    failed = []

    for u_id in user_ids:
        try:
            name = None
            username = None
            if u_id in user_info_map:
                name = user_info_map[u_id].get('name')
                username = user_info_map[u_id].get('username')
            else:
                try:
                    u_obj = await client.get_users(u_id)
                    if u_obj:
                        name = f"{u_obj.first_name or ''} {u_obj.last_name or ''}".strip() or None
                        username = u_obj.username
                except Exception:
                    pass

            if not name:
                doc = await get_special_user(u_id) or await get_user(u_id)
                if doc:
                    name = doc.get('name')
                    if not username:
                        username = doc.get('username')

            uname_str = f" (@{username})" if username else ""
            display = f"<a href='tg://user?id={u_id}'>{html.escape(name)}</a>{uname_str} (<code>{u_id}</code>)" if name else f"<code>{u_id}</code>"

            if await present_special_user(u_id):
                if name or username:
                    await add_special_user(u_id, name=name, username=username)
                already_present.append(display)
            else:
                await add_special_user(u_id, name=name, username=username)
                added.append(display)
        except Exception as e:
            failed.append(f"{u_id} ({e})")

    res = []
    if added:
        res.append(f"✅ <b>Added to special users:</b>\n" + "\n".join([f"• {i}" for i in added]))
    if already_present:
        res.append(f"ℹ️ <b>Already in special users:</b>\n" + "\n".join([f"• {i}" for i in already_present]))
    if failed:
        res.append(f"❌ <b>Failed:</b>\n" + ", ".join(failed))

    await message.reply_text("\n\n".join(res), quote=True)


@Bot.on_message(filters.command('remove') & filters.private & filters.user(ADMINS))
async def remove_special_user_handler(client: Bot, message: Message):
    user_ids = []
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user or message.reply_to_message.forward_from
        if target_user:
            user_ids.append(target_user.id)

    if len(message.command) > 1:
        for arg in message.command[1:]:
            try:
                user_ids.append(int(arg))
            except ValueError:
                await message.reply_text(f"❌ Invalid user ID: <code>{arg}</code>. User ID must be an integer.", quote=True)
                return

    if not user_ids:
        msg_text = (
            "<b>Usage:</b>\n"
            "• <code>/remove [user_id]</code> - Remove user from special users list\n"
            "• <code>/remove [id1] [id2] ...</code> - Remove multiple users\n"
            "• Reply to a user's message with <code>/remove</code>"
        )
        await message.reply_text(msg_text, quote=True)
        return

    user_ids = list(dict.fromkeys(user_ids))
    removed = []
    not_found = []
    failed = []

    for u_id in user_ids:
        try:
            if await present_special_user(u_id):
                doc = await get_special_user(u_id) or await get_user(u_id)
                name = doc.get('name') if doc else None
                username = doc.get('username') if doc else None
                if not name:
                    try:
                        u_obj = await client.get_users(u_id)
                        if u_obj:
                            name = f"{u_obj.first_name or ''} {u_obj.last_name or ''}".strip() or None
                            username = u_obj.username
                    except Exception:
                        pass

                await del_special_user(u_id)
                uname_str = f" (@{username})" if username else ""
                display = f"<a href='tg://user?id={u_id}'>{html.escape(name)}</a>{uname_str} (<code>{u_id}</code>)" if name else f"<code>{u_id}</code>"
                removed.append(display)
            else:
                not_found.append(f"<code>{u_id}</code>")
        except Exception as e:
            failed.append(f"{u_id} ({e})")

    res = []
    if removed:
        res.append(f"✅ <b>Removed from special users:</b>\n" + "\n".join([f"• {i}" for i in removed]))
    if not_found:
        res.append(f"❌ <b>Not found in special users:</b>\n" + ", ".join([f"• {i}" for i in not_found]))
    if failed:
        res.append(f"⚠️ <b>Failed:</b>\n" + ", ".join(failed))

    await message.reply_text("\n\n".join(res), quote=True)


@Bot.on_message(filters.command(['special_users', 'specialusers', 'special']) & filters.private & filters.user(ADMINS))
async def list_special_users_command(client: Bot, message: Message):
    users = await full_special_userbase()
    if not users:
        await message.reply_text("ℹ️ No special users found in the database.", quote=True)
        return

    wait_msg = await message.reply_text("<i>Fetching special users list...</i>", quote=True)

    formatted_users = []
    plain_users = []

    for idx, uid in enumerate(users, start=1):
        name = None
        username = None

        # 1. Try to fetch directly from Telegram client
        try:
            user_obj = await client.get_users(uid)
            if user_obj:
                full_name = f"{user_obj.first_name or ''} {user_obj.last_name or ''}".strip()
                if full_name:
                    name = full_name
                username = user_obj.username
                try:
                    await add_special_user(uid, name=name, username=username)
                except Exception:
                    pass
        except Exception:
            pass

        # 2. Fallback to database if client.get_users failed
        if not name:
            try:
                doc = await get_special_user(uid) or await get_user(uid)
                if doc:
                    name = doc.get('name')
                    if not username:
                        username = doc.get('username')
            except Exception:
                pass

        # 3. Format lines
        if name:
            escaped_name = html.escape(name)
            uname_str = f" (@{username})" if username else ""
            html_line = f"• <a href='tg://user?id={uid}'>{escaped_name}</a>{uname_str} - <code>{uid}</code>"
            plain_line = f"{idx}. {name}{uname_str} - ID: {uid}"
        else:
            uname_str = f" (@{username})" if username else ""
            html_line = f"• <i>Hidden / Unavailable</i>{uname_str} - <code>{uid}</code>"
            plain_line = f"{idx}. ID: {uid} (Name Unavailable){uname_str}"

        formatted_users.append(html_line)
        plain_users.append(plain_line)

    user_list_str = "\n".join(formatted_users)
    text = f"<b>Total Special Users:</b> <code>{len(users)}</code>\n\n<b>Special Users:</b>\n{user_list_str}"

    if len(text) > 4000:
        file_name = "special_users.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(f"Total Special Users: {len(users)}\n\n" + "\n".join(plain_users))
        await message.reply_document(
            document=file_name,
            caption=f"<b>Total Special Users:</b> <code>{len(users)}</code>",
            quote=True
        )
        await wait_msg.delete()
        if os.path.exists(file_name):
            os.remove(file_name)
    else:
        await wait_msg.edit_text(text, disable_web_page_preview=True)


