from typing import Optional, List

from telegram import Message, Chat, Update, Bot
from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, Filters, CommandHandler, run_async
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.welcome_sql as sql
from tg_bot import dispatcher, OWNER_ID
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.string_handling import button_markdown_parser, markdown_parser, \
    escape_invalid_curly_brackets

VALID_WELCOME_FORMATTERS = ['first', 'last', 'fullname', 'username', 'id', 'count', 'chatname', 'mention']

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}


@run_async
def new_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    should_welc, cust_welcome, welc_type = sql.get_welc_pref(chat.id)
    if should_welc:
        new_members = update.effective_message.new_chat_members
        for new_mem in new_members:
            # Give the owner a special welcome
            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text("Master is in the houseeee, let's get this party started!")
                continue
            # Don't welcome yourself
            elif not new_mem.id == bot.id:
                if welc_type != sql.Types.TEXT and welc_type != sql.Types.BUTTON_TEXT:
                    ENUM_FUNC_MAP[welc_type](chat.id, cust_welcome)
                    return

                first_name = new_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.
                if cust_welcome:
                    if new_mem.last_name:
                        fullname = "{} {}".format(first_name, new_mem.last_name)
                    else:
                        fullname = first_name
                    count = chat.get_members_count()
                    mention = "[{}](tg://user?id={})".format(first_name, new_mem.id)
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(cust_welcome, VALID_WELCOME_FORMATTERS)
                    res = valid_format.format(first=escape_markdown(first_name),
                                              last=escape_markdown(new_mem.last_name or first_name),
                                              fullname=escape_markdown(fullname), username=username, mention=mention,
                                              count=count, chatname=escape_markdown(chat.title), id=new_mem.id)
                else:
                    res = sql.DEFAULT_WELCOME.format(first=first_name)

                buttons = sql.get_welc_buttons(chat.id)
                keyb = [[InlineKeyboardButton(btn.name, url=btn.url)] for btn in buttons]
                keyboard = InlineKeyboardMarkup(keyb)

                try:
                    update.effective_message.reply_text(res, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
                except IndexError:

                    update.effective_message.reply_text(markdown_parser(sql.DEFAULT_WELCOME.format(first=first_name) +
                                                                        "\nNote: the current welcome message was "
                                                                        "invalid due to markdown issues. Could be "
                                                                        "due to the user's name."),
                                                        parse_mode=ParseMode.MARKDOWN)
                except KeyError:
                    update.effective_message.reply_text(markdown_parser(sql.DEFAULT_WELCOME.format(first=first_name) +
                                                                        "\nNote: the current welcome message is "
                                                                        "invalid due to an issue with some misplaced "
                                                                        "curly brackets. Please update"),
                                                        parse_mode=ParseMode.MARKDOWN)


@run_async
def left_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)
    if should_goodbye:
        left_mem = update.effective_message.left_chat_member
        if left_mem:
            # Ignore bot being kicked
            if left_mem.id == bot.id:
                return

            # Give the owner a special goodbye
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text("RIP Master")
                return

            if goodbye_type != sql.Types.TEXT and goodbye_type != sql.Types.BUTTON_TEXT:
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
                return

            first_name = left_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.
            if cust_goodbye:
                if left_mem.last_name:
                    fullname = "{} {}".format(first_name, left_mem.last_name)
                else:
                    fullname = first_name
                count = chat.get_members_count()
                mention = "[{}](tg://user?id={})".format(first_name, left_mem.id)
                if left_mem.username:
                    username = "@" + escape_markdown(left_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(cust_goodbye, VALID_WELCOME_FORMATTERS)
                res = valid_format.format(first=escape_markdown(first_name),
                                          last=escape_markdown(left_mem.last_name or first_name),
                                          fullname=escape_markdown(fullname), username=username, mention=mention,
                                          count=count, chatname=escape_markdown(chat.title), id=left_mem.id)
            else:
                res = sql.DEFAULT_GOODBYE

            buttons = sql.get_gdbye_buttons(chat.id)
            keyb = [[InlineKeyboardButton(btn.name, url=btn.url)] for btn in buttons]
            keyboard = InlineKeyboardMarkup(keyb)

            try:
                update.effective_message.reply_text(res, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
            except IndexError:
                update.effective_message.reply_text(markdown_parser(sql.DEFAULT_GOODBYE + "\nNote: the current goodbye "
                                                                                          "message is invalid due to "
                                                                                          "markdown issues. "
                                                                                          " Please update."),
                                                    parse_mode=ParseMode.MARKDOWN)
            except KeyError:
                update.effective_message.reply_text(markdown_parser(sql.DEFAULT_GOODBYE + "\nNote: the current leave "
                                                                                          "message is invalid due to "
                                                                                          "misplaced curly brackets. "
                                                                                          " Please update."),
                                                    parse_mode=ParseMode.MARKDOWN)


@run_async
@user_admin
def welcome(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    # if no args, show current replies.
    if len(args) == 0:
        pref, welcome_m, welcome_type = sql.get_welc_pref(chat.id)
        update.effective_message.reply_text(
            "This chat has it's welcome setting set to: `{}`.\n*The welcome message is:*".format(pref),
            parse_mode=ParseMode.MARKDOWN)
        ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_welc_preference(str(chat.id), True)
            update.effective_message.reply_text("I'll be polite!")

        elif args[0].lower() in ("off", "no"):
            sql.set_welc_preference(str(chat.id), False)
            update.effective_message.reply_text("I'm sulking, not saying hello anymore.")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("I understand 'on/yes' or 'off/no' only!")


@run_async
@user_admin
def goodbye(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]

    if len(args) == 0:
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        update.effective_message.reply_text(
            "This chat has it's goodbye setting set to: `{}`.\n*The goodbye message is:*".format(pref),
            parse_mode=ParseMode.MARKDOWN)
        ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_gdbye_preference(str(chat.id), True)
            update.effective_message.reply_text("I'll be sorry when people leave!")

        elif args[0].lower() in ("off", "no"):
            sql.set_gdbye_preference(str(chat.id), False)
            update.effective_message.reply_text("They leave, they're dead to me.")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("I understand 'on/yes' or 'off/no' only!")


@run_async
@user_admin
def set_welcome(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]
    raw_text = msg.text
    args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args

    buttons = []
    # determine what the contents of the filter are - text, image, sticker, etc
    if len(args) >= 2:
        offset = len(args[1]) - len(msg.text)  # set correct offset relative to command + notename
        content, buttons = button_markdown_parser(args[1], entities=msg.parse_entities(), offset=offset)
        if buttons:
            data_type = sql.Types.BUTTON_TEXT
        else:
            data_type = sql.Types.TEXT

    elif msg.reply_to_message and msg.reply_to_message.sticker:
        content = msg.reply_to_message.sticker.file_id
        data_type = sql.Types.STICKER

    elif msg.reply_to_message and msg.reply_to_message.document:
        content = msg.reply_to_message.document.file_id
        data_type = sql.Types.DOCUMENT

    elif msg.reply_to_message and msg.reply_to_message.photo:
        content = msg.reply_to_message.photo[-1].file_id  # last elem = best quality
        data_type = sql.Types.PHOTO

    elif msg.reply_to_message and msg.reply_to_message.audio:
        content = msg.reply_to_message.audio.file_id
        data_type = sql.Types.AUDIO

    elif msg.reply_to_message and msg.reply_to_message.voice:
        content = msg.reply_to_message.voice.file_id
        data_type = sql.Types.VOICE

    elif msg.reply_to_message and msg.reply_to_message.video:
        content = msg.reply_to_message.video.file_id
        data_type = sql.Types.VIDEO

    else:
        msg.reply_text("You didn't specify what to reply with!")
        return

    sql.set_custom_welcome(chat_id, content, data_type, buttons)
    update.effective_message.reply_text("Successfully set custom welcome message!")


@run_async
@user_admin
def reset_welcome(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    sql.set_custom_welcome(chat_id, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    update.effective_message.reply_text("Successfully reset welcome message to default!")


@run_async
@user_admin
def set_goodbye(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]
    raw_text = msg.text
    args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args

    buttons = []
    # determine what the contents of the filter are - text, image, sticker, etc
    if len(args) >= 2:
        offset = len(args[1]) - len(msg.text)  # set correct offset relative to command + notename
        content, buttons = button_markdown_parser(args[1], entities=msg.parse_entities(), offset=offset)
        if buttons:
            data_type = sql.Types.BUTTON_TEXT
        else:
            data_type = sql.Types.TEXT

    elif msg.reply_to_message and msg.reply_to_message.sticker:
        content = msg.reply_to_message.sticker.file_id
        data_type = sql.Types.STICKER

    elif msg.reply_to_message and msg.reply_to_message.document:
        content = msg.reply_to_message.document.file_id
        data_type = sql.Types.DOCUMENT

    elif msg.reply_to_message and msg.reply_to_message.photo:
        content = msg.reply_to_message.photo[-1].file_id  # last elem = best quality
        data_type = sql.Types.PHOTO

    elif msg.reply_to_message and msg.reply_to_message.audio:
        content = msg.reply_to_message.audio.file_id
        data_type = sql.Types.AUDIO

    elif msg.reply_to_message and msg.reply_to_message.voice:
        content = msg.reply_to_message.voice.file_id
        data_type = sql.Types.VOICE

    elif msg.reply_to_message and msg.reply_to_message.video:
        content = msg.reply_to_message.video.file_id
        data_type = sql.Types.VIDEO

    else:
        msg.reply_text("You didn't specify what to reply with!")
        return

    sql.set_custom_gdbye(chat_id, content, data_type, buttons)
    update.effective_message.reply_text("Successfully set custom goodbye message!")


@run_async
@user_admin
def reset_goodbye(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    sql.set_custom_gdbye(chat_id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    update.effective_message.reply_text("Successfully reset goodbye message to default!")


WELC_HELP_TXT = "Your group's welcome/goodbye messages can be personalised in multiple ways. If you want the messages " \
                "to be individually generated, like the default welcome message is, you can use *these* variables:\n" \
                " - `{{first}}`: this represents the user's *first* name\n" \
                " - `{{last}}`: this represents the user's *last* name. Defaults to *first name* if user has no " \
                "last name.\n" \
                " - `{{fullname}}`: this represents the user's *full* name. Defaults to *first name* if user has no " \
                "last name.\n" \
                " - `{{username}}`: this represents the user's *username*. Defaults to a *mention* of the user's " \
                "first name if has no username.\n" \
                " - `{{mention}}`: this simply *mentions* a user - tagging them with their first name.\n" \
                " - `{{id}}`: this represents the user's *id*\n" \
                " - `{{count}}`: this represents the user's *member number*.\n" \
                " - `{{chatname}}`: this represents the *current chat name*.\n" \
                "\nEach variable MUST be surrounded by `{{}}` to be replaced.\n" \
                "Welcome messages also support markdown, so you can make any elements bold/italic/code/links." \
                "Buttons are also supported, so you can make your welcomes look damn good with some sexy intro " \
                "buttons.\n" \
                "To create a button linking to your rules, use this: `[Rules](buttonurl://t.me/{}?start=group_id)`. " \
                "Simply replace `group_id` with your group's id, which can be obtained via /id, and you're good to " \
                "go.\n" \
                "If you're feeling fun, you can even set images/gifs/videos/voice messages as the welcome message by " \
                "replying to the desired media, and calling /setwelcome.".format(dispatcher.bot.username)


@run_async
@user_admin
def welcome_help(bot: Bot, update: Update):
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


# TODO: get welcome data from group butler snap
# def __import_data__(chat_id, data):
#     welcome = data.get('info', {}).get('rules')
#     welcome = welcome.replace('$username', '{username}')
#     welcome = welcome.replace('$name', '{fullname}')
#     welcome = welcome.replace('$id', '{id}')
#     welcome = welcome.replace('$title', '{chatname}')
#     welcome = welcome.replace('$surname', '{lastname}')
#     welcome = welcome.replace('$rules', '{rules}')
#     sql.set_custom_welcome(chat_id, welcome, sql.Types.TEXT)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref, welcome_m, welcome_type = sql.get_welc_pref(chat_id)
    goodbye_pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat_id)
    return "This chat has it's welcome preference set to `{}`.\n" \
           "It's goodbye preference is `{}`.".format(welcome_pref, goodbye_pref)


__help__ = """
*Admin only:*
 - /welcome <on/off>: enable/disable welcome messages. If used with no arg, shows current settings.
 - /goodbye <on/off>: enable/disable goodbye messages. If used with no arg, shows current settings.
 - /setwelcome <sometext>: set a custom welcome message. If used replying to media, uses that media.
 - /setgoodbye <sometext>: set a custom goodbye message. If used replying to media, uses that media.
 - /resetwelcome: reset to the default welcome message.
 - /resetgoodbye: reset to the default goodbye message.
 - /welcomehelp: view more formatting information for custom welcome/goodbye messages.
"""

__name__ = "Welcomes/Goodbyes"

NEW_MEM_HANDLER = MessageHandler(Filters.status_update.new_chat_members, new_member)
LEFT_MEM_HANDLER = MessageHandler(Filters.status_update.left_chat_member, left_member)
WELC_PREF_HANDLER = CommandHandler("welcome", welcome, pass_args=True, filters=Filters.group)
GOODBYE_PREF_HANDLER = CommandHandler("goodbye", goodbye, pass_args=True, filters=Filters.group)
SET_WELCOME = CommandHandler("setwelcome", set_welcome, filters=Filters.group)
SET_GOODBYE = CommandHandler("setgoodbye", set_goodbye, filters=Filters.group)
RESET_WELCOME = CommandHandler("resetwelcome", reset_welcome, filters=Filters.group)
RESET_GOODBYE = CommandHandler("resetgoodbye", reset_goodbye, filters=Filters.group)
WELCOME_HELP = CommandHandler("welcomehelp", welcome_help)

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(WELCOME_HELP)
