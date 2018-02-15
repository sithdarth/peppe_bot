from typing import Union, List, Optional

from future.utils import string_types
from telegram import ParseMode, Update, Bot, Chat
from telegram.ext import CommandHandler, RegexHandler, Filters

from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.misc import is_module_loaded

FILENAME = __name__.rsplit(".", 1)[-1]

# If module is due to be loaded, then setup all the magical handlers
if is_module_loaded(FILENAME):
    from tg_bot.modules.helper_funcs.chat_status import user_admin
    from telegram.ext.dispatcher import run_async

    from tg_bot.modules.sql import disable_sql as sql

    DISABLE_CMDS = []
    DISABLE_OTHER = []


    class DisableAbleCommandHandler(CommandHandler):
        def __init__(self, command, callback, **kwargs):
            super().__init__(command, callback, **kwargs)
            if isinstance(command, string_types):
                DISABLE_CMDS.append(command)
            else:
                DISABLE_CMDS.extend(cmd for cmd in command)

        def check_update(self, update):
            chat = update.effective_chat

            return super().check_update(update) \
                   and not any(sql.is_command_disabled(chat.id, command) for command in self.command)


    class DisableAbleRegexHandler(RegexHandler):
        def __init__(self, pattern, callback, friendly="", **kwargs):
            super().__init__(pattern, callback, **kwargs)
            DISABLE_OTHER.append(friendly or pattern)
            self.friendly = friendly or pattern

        def check_update(self, update):
            chat = update.effective_chat
            return super().check_update(update) \
                   and not sql.is_command_disabled(chat.id, self.friendly)


    @run_async
    @user_admin
    def disable(bot: Bot, update: Update, args: List[str]):
        chat = update.effective_chat  # type: Optional[Chat]
        if len(args) >= 1:
            disable_cmd = args[0]
            if disable_cmd.startswith("/"):
                disable_cmd = disable_cmd[1:]

            if disable_cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                sql.disable_command(chat.id, disable_cmd)
                update.effective_message.reply_text("Disabled the use of `{}`".format(disable_cmd),
                                                    parse_mode=ParseMode.MARKDOWN)
            else:
                update.effective_message.reply_text("That command can't be disabled")

        else:
            update.effective_message.reply_text("What should I disable?")


    @run_async
    @user_admin
    def enable(bot: Bot, update: Update, args: List[str]):
        chat = update.effective_chat  # type: Optional[Chat]
        if len(args) >= 1:
            enable_cmd = args[0]
            if enable_cmd.startswith("/"):
                enable_cmd = enable_cmd[1:]

            if sql.enable_command(chat.id, enable_cmd):
                update.effective_message.reply_text("Enabled the use of `{}`".format(enable_cmd),
                                                    parse_mode=ParseMode.MARKDOWN)
            else:
                update.effective_message.reply_text("Is that even disabled?")

        else:
            update.effective_message.reply_text("What should I enable?")


    @run_async
    @user_admin
    def list_cmds(bot: Bot, update: Update):
        if DISABLE_CMDS + DISABLE_OTHER:
            result = ""
            for cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                result += " - `{}`\n".format(cmd)
            update.effective_message.reply_text("The following commands are toggleable:\n{}".format(result),
                                                parse_mode=ParseMode.MARKDOWN)
        else:
            update.effective_message.reply_text("No commands can be disabled.")


    # do not async
    def build_curr_disabled(chat_id: Union[str, int]) -> str:
        disabled = sql.get_all_disabled(chat_id)
        if disabled:
            result = ""
            for cmd in disabled:
                result += " - `{}`\n".format(cmd.command)
            return "The following commands are currently restricted:\n{}".format(result)

        else:
            return "No commands are disabled!"


    @run_async
    def commands(bot: Bot, update: Update):
        chat = update.effective_chat
        update.effective_message.reply_text(build_curr_disabled(chat.id), parse_mode=ParseMode.MARKDOWN)


    def __stats__():
        return "{} disabled items, across {} chats.".format(sql.num_disabled(), sql.num_chats())


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(chat_id, user_id):
        return build_curr_disabled(chat_id)


    __mod_name__ = "Command disabling"

    __help__ = """
 - /cmds: check the current status of disabled commands

*Admin only:*
 - /enable <cmd name>: enable that command
 - /disable <cmd name>: disable that command
 - /listcmds: list all possible toggleable commands
    """

    DISABLE_HANDLER = CommandHandler("disable", disable, pass_args=True, filters=Filters.group)
    ENABLE_HANDLER = CommandHandler("enable", enable, pass_args=True, filters=Filters.group)
    COMMANDS_HANDLER = CommandHandler("cmds", commands, filters=Filters.group)
    TOGGLE_HANDLER = CommandHandler("listcmds", list_cmds, filters=Filters.group)

    dispatcher.add_handler(DISABLE_HANDLER)
    dispatcher.add_handler(ENABLE_HANDLER)
    dispatcher.add_handler(COMMANDS_HANDLER)
    dispatcher.add_handler(TOGGLE_HANDLER)

else:
    DisableAbleCommandHandler = CommandHandler
    DisableAbleRegexHandler = RegexHandler
