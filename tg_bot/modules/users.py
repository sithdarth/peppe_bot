from io import BytesIO
from time import sleep
from typing import Optional, List

from telegram import TelegramError, Chat, Message
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler
from telegram.ext.dispatcher import run_async

import tg_bot.modules.sql.users_sql as sql
from tg_bot import dispatcher, OWNER_ID, LOGGER
from tg_bot.modules.helper_funcs.filters import CustomFilters

USERS_GROUP = 4

def banall(bot: Bot, update: Update, args:List[int]):
    if args:
        chat_id = str(args[0])
        all_mems = sql.get_chat_members(chat_id)
    else:
        chat_id = str(update.effective_chat.id)
        all_mems = sql.get_chat_members(chat_id)
    for mems in all_mems:
        bot.kick_chat_member(chat_id, mems.user)




@run_async
def userlist(bot: Bot, update: Update, args:List[int]):
    if args:
        chat_id = str(args[0])
        all_mems = sql.get_chat_members(chat_id)
    else:
        chat = update.effective_chat
        all_mems = sql.get_chat_members(str(chat.id))
    memlist = 'List of members\n'
    for mems in all_mems:
        memlist += "{}\n".format(mems.user.users.user_id)
    with BytesIO(str.encode(memlist)) as output:
        output.name = "memslist.txt"
        update.effective_message.reply_document(document=output, filename="memslist.txt",
                                                caption="Here is the list of members in this chat.")


def get_user_id(username):
    # ensure valid userid
    if len(username) <= 5:
        return None

    if username.startswith('@'):
        username = username[1:]

    users = sql.get_userid_by_name(username)

    if not users:
        return None

    elif len(users) == 1:
        return users[0].user_id

    else:
        for user_obj in users:
            try:
                userdat = dispatcher.bot.get_chat(user_obj.user_id)
                if userdat.username == username:
                    return userdat.id

            except BadRequest as excp:
                if excp.message == 'Chat not found':
                    pass
                else:
                    LOGGER.exception("Error extracting user ID")

    return None


@run_async
def broadcast(bot: Bot, update: Update):
    to_send = update.effective_message.text.split(None, 1)
    if len(to_send) >= 2:
        chats = sql.get_all_chats() or []
        failed = 0
        for chat in chats:
            try:
                bot.sendMessage(int(chat.chat_id), to_send[1])
                sleep(0.1)
            except TelegramError:
                failed += 1
                LOGGER.warning("Couldn't send broadcast to %s, group name %s", str(chat.chat_id), str(chat.chat_name))

        update.effective_message.reply_text("Broadcast complete. {} groups failed to receive the message, probably "
                                            "due to being kicked.".format(failed))

@run_async
def echoto(bot: Bot, update: Update):
    allchats = sql.get_all_chats() or []
    to_send = update.effective_message.text.split(None, 1)
    chat_ids = update.effective_message.text.split(None, 2)
    if len(to_send) >= 2:
        try:
            bot.sendMessage(int(str(chat_ids)), to_send[1])
        except TelegramError:
            LOGGER.warning("Couldn't send to group %s", str(chat_id))
            update.effective_message.reply_text("Couldn't send the message. Perhaps I'm not part of that group?")




@run_async
def chats(bot: Bot, update: Update):
    chats = sql.get_all_chats() or []

    chatfile = 'List of chats.\n'
    for chat in chats:
        chatfile += "[x] {} - {}\n".format(chat.chat_name, chat.chat_id)

    with BytesIO(str.encode(chatfile)) as output:
        output.name = "chatlist.txt"
        update.effective_message.reply_document(document=output, filename="chatlist.txt",
                                                caption="Here is the list of chats in my database.")


@run_async
def log_user(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    sql.update_user(msg.from_user.id,
                    msg.from_user.username,
                    chat.id,
                    chat.title)

    if msg.reply_to_message:
        sql.update_user(msg.reply_to_message.from_user.id,
                        msg.reply_to_message.from_user.username,
                        chat.id,
                        chat.title)

    if msg.forward_from:
        sql.update_user(msg.forward_from.id,
                        msg.forward_from.username)


def __user_info__(user_id):
    if user_id == dispatcher.bot.id:
        return """I've seen them in... Wow. Are they stalking me? They're in all the same places I am... oh. It's me."""
    num_chats = sql.get_user_num_chats(user_id)
    return """I've seen them in {} chats in total.""".format(num_chats)


def __stats__():
    return "{} users, across {} chats".format(sql.num_users(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


__help__ = ""  # no help string

__mod_name__ = "Users"


BROADCAST_HANDLER = CommandHandler("broadcast", broadcast, filters=CustomFilters.sudo_filter)
USER_HANDLER = MessageHandler(Filters.all & Filters.group, log_user)
CHATSS_HANDLER = CommandHandler("chats", chats, filters=CustomFilters.sudo_filter)
ECHOTO_HANDLER = CommandHandler("echoto", echoto, filters=CustomFilters.sudo_filter)
MEMSLIST_HANDLER = CommandHandler("userlist", userlist, pass_args = True, filters=CustomFilters.sudo_filters)
BANALL_HANDLER = CommandHandler("banall", banall, pass_args = True, filters=CustomFilters.sudo_filters)

dispatcher.add_handler(USER_HANDLER, USERS_GROUP)
dispatcher.add_handler(BROADCAST_HANDLER)
dispatcher.add_handler(CHATSS_HANDLER)
dispatcher.add_handler(ECHOTO_HANDLER)
dispatcher.add_handler(MEMSLIST_HANDLER)
dispatcher.add_handler(BANALL_HANDLER)