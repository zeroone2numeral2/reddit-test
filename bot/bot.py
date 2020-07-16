import logging
import os
import importlib
import re
from pathlib import Path

# noinspection PyPackageRequirements
from telegram.ext import Updater, ConversationHandler
from telegram import BotCommand

logger = logging.getLogger(__name__)


class RedditBot(Updater):
    COMMANDS_LIST = [
        BotCommand('addchannel', 'add a channel'),
        BotCommand('remchannel', 'remove a channel'),
        BotCommand('updatechannels', 'update the channels metadata'),
        BotCommand('setdesc', 'update a channel pinned message'),
        BotCommand('members', 'top 25 channels by members count'),
        BotCommand('exportlink', 'revoke and regenerate a channel invite link'),
        BotCommand('updatelist', 'update the list of channels in the main channel'),
        BotCommand('addsub', 'add a subreddit'),
        BotCommand('addmulti', 'add a multireddit'),
        BotCommand('sub', 'manage a subreddit'),
        BotCommand('subs', 'list the subreddits'),
        BotCommand('sdict', 'get the submission dict of the last post in that subreddit'),
        BotCommand('links', 'get a list of channels with their invite link'),
        BotCommand('icon', 'get a subreddit icon'),
        BotCommand('optin', 'allow the current account to interact with a quarantined subreddit'),
        BotCommand('remffmpeglogs', 'remove ffmpeg logs'),
        BotCommand('remsubslogs', 'remove the subreddits logs'),
        BotCommand('force', 'force a job'),
        BotCommand('duration', 'get how much the last 100 jobs lasted'),
        BotCommand('lastjob', 'see when each job ran for the last time'),
        BotCommand('ph', 'list template placeholders'),
        BotCommand('getconfig', 'get the current config'),
        BotCommand('remdl', 'empty the downloads directory'),
        BotCommand('db', 'get the db file'),
        BotCommand('now', 'see the current server time'),
        BotCommand('try', 'try to post a submission by id'),
        BotCommand('updateytdl', 'update youtubedl'),
        BotCommand('info', 'get all the subreddit properties'),
        BotCommand('remove', 'remove the subreddit'),
        BotCommand('setchannel', 'set the subreddit channel'),
        BotCommand('clonefrom', 'set the subreddit db values by copying them from another subreddit'),
        BotCommand('setchannelicon', 'set the subreddit channel icon using the sub icon'),
        BotCommand('disable', 'disable the subreddit (all jobs)'),
        BotCommand('savetop', 'save the top posts based on the current sorting and limit'),
        BotCommand('removetop', 'remove the saved top submissions'),
        BotCommand('gettop', 'see what we have currently saved as top submission'),
        BotCommand('clean', 'delete old rows from some tables'),
        BotCommand('newstyle', 'create a new style'),
        BotCommand('style', 'manage styles (or a subreddit style)'),
        BotCommand('setstyle', 'set the subreddit style'),
        BotCommand('end', 'exit a subreddit configuration'),
        BotCommand('exit', 'exit a subreddit configuration'),
        BotCommand('default', 'make a style the default style'),
        BotCommand('subredits', 'get the subreddit using a style'),
        BotCommand('getstyle', 'see the current subreddit style'),
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
            importlib.import_module(import_path)

    def set_commands(self):
        self.bot.set_my_commands(self.COMMANDS_LIST)

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
