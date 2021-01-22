import logging
import os
import importlib
import re
from pathlib import Path

# noinspection PyPackageRequirements
from telegram.ext import Updater, CommandHandler, ConversationHandler
from telegram import BotCommand

logger = logging.getLogger(__name__)


class DummyJob:
    def __init__(self, name):
        self.name = name


class DummyContext:
    def __init__(self, updater, job_name):
        self.updater = updater
        self.job = DummyJob(job_name)


class RedditBot(Updater):
    # COMMANDS_LIST_DETECTED = []
    # COMMANDS_LIST = []

    @staticmethod
    def _load_manifest(manifest_path):
        if not manifest_path:
            return

        try:
            with open(manifest_path, 'r') as f:
                manifest_str = f.read()
        except FileNotFoundError:
            logger.debug('manifest <%s> not found', os.path.normpath(manifest_path))
            return

        if not manifest_str.strip():
            return

        manifest_str = manifest_str.replace('\r\n', '\n')
        manifest_lines = manifest_str.split('\n')

        modules_list = list()
        for line in manifest_lines:
            line = re.sub(r'(?:\s+)?#.*(?:\n|$)', '', line)  # remove comments from the line
            if line.strip():  # ignore empty lines
                items = line.split()  # split on spaces. We will consider only the first word
                modules_list.append(items[0])  # tuple: (module_to_import, [callbacks_list])

        return modules_list

    @classmethod
    def import_handlers(cls, directory):
        """A text file named "manifest" can be placed in the dir we are importing the handlers from.
        It can contain the list of the files to import, the bot will import only these
        modules as ordered in the manifest file.
        Inline comments are allowed, they must start by #"""

        paths_to_import = list()

        manifest_modules = cls._load_manifest(os.path.join(directory, 'manifest'))
        if manifest_modules:
            # build the base import path of the plugins/jobs directory
            target_dir_path = os.path.splitext(directory)[0]
            target_dir_import_path_list = list()
            while target_dir_path:
                target_dir_path, tail = os.path.split(target_dir_path)
                target_dir_import_path_list.insert(0, tail)
            base_import_path = '.'.join(target_dir_import_path_list)

            for module in manifest_modules:
                import_path = base_import_path + module

                logger.debug('importing module: %s', import_path)

                paths_to_import.append(import_path)
        else:
            for path in sorted(Path(directory).rglob('*.py')):
                file_path = os.path.splitext(str(path))[0]

                import_path = []

                while file_path:
                    file_path, tail = os.path.split(file_path)
                    import_path.insert(0, tail)

                import_path = '.'.join(import_path)

                paths_to_import.append(import_path)

        for import_path in paths_to_import:
            logger.debug('importing module: %s', import_path)
            m = importlib.import_module(import_path)
            """
            if not hasattr(m, "_COMMANDS"):
                continue

            logger.debug("importing commands: %s", m._COMMANDS)
            for command in m._COMMANDS:
                command_lower = command.lower()
                if command_lower not in cls.COMMANDS_LIST_DETECTED:
                    cls.COMMANDS_LIST_DETECTED.append(command_lower)
            """

    def set_commands(self, sort_alphabetically=False):
        commands = []
        for group, handlers in self.dispatcher.handlers.items():
            for handler in handlers:
                if isinstance(handler, CommandHandler):
                    commands.extend(handler.command)
                elif isinstance(handler, ConversationHandler):
                    for entry_point_handler in handler.entry_points:
                        if isinstance(entry_point_handler, CommandHandler):
                            commands.extend(entry_point_handler.command)

                    for state, state_handlers in handler.states.items():
                        for state_handler in state_handlers:
                            if isinstance(state_handler, CommandHandler):
                                commands.extend(state_handler.command)

                    for fallback_handler in handler.fallbacks:
                        if isinstance(fallback_handler, CommandHandler):
                            commands.extend(fallback_handler.command)

        commands = list(set(commands))  # remove duplicates

        if sort_alphabetically:
            commands.sort()

        commands_list = [BotCommand(command, "command placeholder") for command in commands]
        self.bot.set_my_commands(commands_list)

    def ongoing_conversation(self, user_id, chat_id):
        for group, handlers in self.dispatcher.handlers.items():
            for handler in handlers:
                if not isinstance(handler, ConversationHandler):
                    continue

                # this is the key format of the ConversationHandler.conevrsations dict
                # https://github.com/python-telegram-bot/python-telegram-bot/blob/0c9915243df7fabe70d827250118a975d705fc6b/telegram/ext/conversationhandler.py#L392
                user_key = (chat_id, user_id)

                user_step = handler.conversations.get(user_key, None)
                if user_step is not None:
                    return True

                # print(handler.name, '::', user_step, get_status_description(user_step))

    def restrict_entry_points(self):
        raise NotImplementedError

        def dummy_callback(a, b):
            pass

        # first, we collect all the entry_point that are a CommandHandler, and creatue a dummy CommandHandler that
        # will later be added to all ConversationHandler
        handlers_to_inject = []
        for group, handlers in self.dispatcher.handlers.items():
            for handler in handlers:
                if not isinstance(handler, ConversationHandler):
                    continue

                for entry_point_handler in handler.entry_points:
                    if isinstance(entry_point_handler, CommandHandler):
                        dummy_handler = CommandHandler(entry_point_handler.command, dummy_callback)
                        handlers_to_inject.extend(dummy_handler)

        # we loop the list again so we can inject the handlers
        # problems:
        # - we have no idea to which state to bind the dummy handlers
        # - we only have to iject the handlers associated with the entry point of OTHER conversations, so we do not
        #   have to add the CommandHandler entry point of the current ConversationHandler
        for group, handlers in self.dispatcher.handlers.items():
            for handler in handlers:
                if not isinstance(handler, ConversationHandler):
                    continue

    def run(self, *args, set_commands=True, **kwargs):
        if set_commands:
            logger.info('updating commands list...')
            self.set_commands()

        logger.info('running as @%s', self.bot.username)
        self.start_polling(*args, **kwargs)
        self.idle()

    def add_handler(self, *args, **kwargs):
        if isinstance(args[0], ConversationHandler):
            # ConverstaionHandler.name or the name of the first entry_point function
            logger.info('adding conversation handler: %s', args[0].name or args[0].entry_points[0].callback.__name__)
        else:
            logger.info('adding handler: %s', args[0].callback.__name__)

        self.dispatcher.add_handler(*args, **kwargs)
