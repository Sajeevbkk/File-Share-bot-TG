#(©)Codexbotz

from aiohttp import web
from plugins import web_server

import pyromod.listen
from pyrogram import Client, raw, utils
from pyrogram.enums import ParseMode
import sys
from datetime import datetime

from config import API_HASH, APP_ID, LOGGER, TG_BOT_TOKEN, TG_BOT_WORKERS, FORCE_SUB_CHANNEL, CHANNEL_ID, PORT, FORWARD_TO_CHANNEL
from helper_func import track_session_message
from database.database import load_banned_users_cache


ascii_art = """
░█████╗░░█████╗░██████╗░███████╗██╗░░██╗██████╗░░█████╗░████████╗███████╗
██╔══██╗██╔══██╗██╔══██╗██╔════╝╚██╗██╔╝██╔══██╗██╔══██╗╚══██╔══╝╚════██║
██║░░╚═╝██║░░██║██║░░██║█████╗░░░╚███╔╝░██████╦╝██║░░██║░░░██║░░░░░███╔═╝
██║░░██╗██║░░██║██║░░██║██╔══╝░░░██╔██╗░██╔══██╗██║░░██║░░░██║░░░██╔══╝░░
╚█████╔╝╚█████╔╝██████╔╝███████╗██╔╝╚██╗██████╦╝╚█████╔╝░░░██║░░░███████╗
░╚════╝░░╚════╝░╚═════╝░╚══════╝╚═╝░░╚═╝╚═════╝░░╚════╝░░░░╚═╝░░░╚══════╝
"""

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={
                "root": "plugins"
            },
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN
        )
        self.LOGGER = LOGGER

    async def start(self):
        await super().start()
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()
        await load_banned_users_cache()

        self.force_sub_chats = {}
        self.invitelinks = {}
        if FORCE_SUB_CHANNEL:
            for ch_id in FORCE_SUB_CHANNEL:
                try:
                    try:
                        f_id = utils.get_channel_id(ch_id)
                        f_res = await self.invoke(raw.functions.channels.GetChannels(id=[raw.types.InputChannel(channel_id=f_id, access_hash=0)]))
                        if f_res and hasattr(f_res, "chats"):
                            await self.fetch_peers(f_res.chats)
                    except Exception:
                        pass
                    force_sub_chat = await self.get_chat(ch_id)
                    self.force_sub_chats[ch_id] = force_sub_chat
                    link = force_sub_chat.invite_link
                    if not link:
                        link = await self.export_chat_invite_link(ch_id)
                        force_sub_chat = await self.get_chat(ch_id)
                        self.force_sub_chats[ch_id] = force_sub_chat
                        link = force_sub_chat.invite_link or link
                    self.invitelinks[ch_id] = link
                except Exception as a:
                    self.LOGGER(__name__).warning(a)
                    self.LOGGER(__name__).warning(f"Bot can't Export Invite link from Force Sub Channel: {ch_id}!")
                    self.LOGGER(__name__).warning(f"Please Double check the FORCE_SUB_CHANNEL value and Make sure Bot is Admin in channel with Invite Users via Link Permission, Current Force Sub Channel Value: {ch_id}")
                    self.LOGGER(__name__).info("\nBot Stopped. Join https://t.me/CodeXBotzSupport for support")
                    sys.exit()

            if self.invitelinks:
                self.invitelink = list(self.invitelinks.values())[0]
                self.force_sub_chat = list(self.force_sub_chats.values())[0]

        try:
            try:
                fwd_id = utils.get_channel_id(FORWARD_TO_CHANNEL)
                fwd_res = await self.invoke(raw.functions.channels.GetChannels(id=[raw.types.InputChannel(channel_id=fwd_id, access_hash=0)]))
                if fwd_res and hasattr(fwd_res, "chats"):
                    await self.fetch_peers(fwd_res.chats)
            except Exception:
                pass
            forward_to_chat = await self.get_chat(FORWARD_TO_CHANNEL)
            self.forward_to_chat = forward_to_chat
            test_fwd = await self.send_message(chat_id=forward_to_chat.id, text="Test Message")
            await test_fwd.delete()
        except Exception as e:
            self.LOGGER(__name__).warning(e)
            self.LOGGER(__name__).warning(f"Make Sure bot is Admin in FORWARD_TO_CHANNEL with Post Messages Permission, and Double check the FORWARD_TO_CHANNEL Value, Current Value {FORWARD_TO_CHANNEL}")
            self.LOGGER(__name__).info("\nBot Stopped. Join https://t.me/CodeXBotzSupport for support")
            sys.exit()
        try:
            try:
                ch_id = utils.get_channel_id(CHANNEL_ID)
                res = await self.invoke(raw.functions.channels.GetChannels(id=[raw.types.InputChannel(channel_id=ch_id, access_hash=0)]))
                if res and hasattr(res, "chats"):
                    await self.fetch_peers(res.chats)
            except Exception:
                pass
            db_channel = await self.get_chat(CHANNEL_ID)
            self.db_channel = db_channel
            test = await self.send_message(chat_id = db_channel.id, text = "Test Message")
            await test.delete()
        except Exception as e:
            self.LOGGER(__name__).warning(e)
            self.LOGGER(__name__).warning(f"Make Sure bot is Admin in DB Channel, and Double check the CHANNEL_ID Value, Current Value {CHANNEL_ID}")
            self.LOGGER(__name__).info("\nBot Stopped. Join https://t.me/CodeXBotzSupport for support")
            sys.exit()

        self.set_parse_mode(ParseMode.HTML)
        self.LOGGER(__name__).info(f"Bot Running..!\n\nCreated by \nhttps://t.me/CodeXBotz")
        try:
            print(ascii_art)
        except UnicodeEncodeError:
            pass
        print("Welcome to CodeXBotz File Sharing Bot")
        self.username = usr_bot_me.username
        #web-response
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    async def send_message(self, chat_id, *args, **kwargs):
        msg = await super().send_message(chat_id, *args, **kwargs)
        if msg and hasattr(msg, 'id'):
            track_session_message(chat_id, msg.id)
        return msg

    async def copy_message(self, chat_id, *args, **kwargs):
        msg = await super().copy_message(chat_id, *args, **kwargs)
        if msg and hasattr(msg, 'id'):
            track_session_message(chat_id, msg.id)
        return msg

    async def send_cached_media(self, chat_id, *args, **kwargs):
        msg = await super().send_cached_media(chat_id, *args, **kwargs)
        if msg and hasattr(msg, 'id'):
            track_session_message(chat_id, msg.id)
        return msg

    async def send_document(self, chat_id, *args, **kwargs):
        msg = await super().send_document(chat_id, *args, **kwargs)
        if msg and hasattr(msg, 'id'):
            track_session_message(chat_id, msg.id)
        return msg

    async def send_photo(self, chat_id, *args, **kwargs):
        msg = await super().send_photo(chat_id, *args, **kwargs)
        if msg and hasattr(msg, 'id'):
            track_session_message(chat_id, msg.id)
        return msg

    async def send_video(self, chat_id, *args, **kwargs):
        msg = await super().send_video(chat_id, *args, **kwargs)
        if msg and hasattr(msg, 'id'):
            track_session_message(chat_id, msg.id)
        return msg

    async def send_audio(self, chat_id, *args, **kwargs):
        msg = await super().send_audio(chat_id, *args, **kwargs)
        if msg and hasattr(msg, 'id'):
            track_session_message(chat_id, msg.id)
        return msg

    async def send_animation(self, chat_id, *args, **kwargs):
        msg = await super().send_animation(chat_id, *args, **kwargs)
        if msg and hasattr(msg, 'id'):
            track_session_message(chat_id, msg.id)
        return msg

    async def send_voice(self, chat_id, *args, **kwargs):
        msg = await super().send_voice(chat_id, *args, **kwargs)
        if msg and hasattr(msg, 'id'):
            track_session_message(chat_id, msg.id)
        return msg
