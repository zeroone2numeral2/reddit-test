import logging
import os
import importlib
import re
from pathlib import Path

# noinspection PyPackageRequirements
from telegram.ext import Updater, ConversationHandler
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
    COMMANDS_LIST_DETECTED = []
    COMMANDS_LIST = [
        BotCommand('help', 'see help message'),
        BotCommand('addchannel', 'command'),
        BotCommand('remchannel', 'command'),
        BotCommand('updatechannels', 'command'),
        BotCommand('updatepin', 'command'),
        BotCommand('members', 'command'),
        BotCommand('exit', 'command'),
        BotCommand('updatelist', 'command'),
        BotCommand('addsub', 'command'),
        BotCommand('addmulti', 'command'),
        BotCommand('sub', 'command'),
        BotCommand('subs', 'command'),
        BotCommand('dailyposts', 'command'),
        BotCommand('submissions', 'command'),
        BotCommand('sdict', 'command'),
        BotCommand('links', 'command'),
        BotCommand('icon', 'command'),
        BotCommand('dailyavg', 'command'),
        BotCommand('flairs', 'command'),
        BotCommand('optin', 'command'),
        BotCommand('remffmpeglogs', 'command'),
        BotCommand('remlogs', 'command'),
        BotCommand('duration', 'command'),
        BotCommand('lastjob', 'command'),
        BotCommand('ph', 'command'),
        BotCommand('getconfig', 'command'),
        BotCommand('remdl', 'command'),
        BotCommand('db', 'command'),
        BotCommand('now', 'command'),
        BotCommand('try', 'command'),
        BotCommand('updateytdl', 'command'),
        BotCommand('info', 'command'),
        BotCommand('remove', 'command'),
        BotCommand('setchannel', 'command'),
        BotCommand('clonefrom', 'command'),
        BotCommand('setchannelicon', 'command'),
        BotCommand('disable', 'command'),
        BotCommand('savetop', 'command'),
        BotCommand('removetop', 'command'),
        BotCommand('gettop', 'command'),
        BotCommand('cleandb', 'command'),
        BotCommand('newstyle', 'command'),
        BotCommand('style', 'command'),
        BotCommand('setstyle', 'command'),
        BotCommand('default', 'command'),
        BotCommand('clone', 'command'),
        BotCommand('exportlink', 'command'),
        BotCommand('subreddits', 'command'),
        BotCommand('getstyle', 'command'),
        BotCommand('rename', 'command'),
        BotCommand('lockstatus', 'command'),
        BotCommand('lock', 'command'),
        BotCommand('unlock', 'command'),
        BotCommand('freq', 'command'),
        BotCommand('getadmins', 'command'),
        BotCommand('credstats', 'command'),
        BotCommand('credsusagemode', 'command'),
        BotCommand('unlinksubs', 'command'),
        BotCommand('updateicon', 'command'),
        BotCommand('updatechat', 'command'),
        BotCommand('channel', 'command'),
        BotCommand('private', 'command'),
        BotCommand('public', 'command'),
        BotCommand('unposted', 'command'),
    ]

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
            if not hasattr(m, "_COMMANDS"):
                continue

            logger.debug("importing commands: %s", m._COMMANDS)
            for command in m._COMMANDS:
                command_lower = command.lower()
                if command_lower not in cls.COMMANDS_LIST_DETECTED:
                    cls.COMMANDS_LIST_DETECTED.append(command_lower)

    def set_commands(self):
        # self.bot.set_my_commands(self.COMMANDS_LIST)
        commands_list = [BotCommand(command, "command") for command in self.COMMANDS_LIST_DETECTED]
        self.bot.set_my_commands(commands_list)

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
