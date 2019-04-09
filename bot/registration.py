import logging
import re
import os
from pathlib import Path

logger = logging.getLogger('plugins')


class Registration:
    list = []
    dispatcher = None

    @classmethod
    def hook(cls, dispatcher, **kwargs):
        cls.dispatcher = dispatcher

    @staticmethod
    def _fetch_valid_callbacks(import_path, callbacks_whitelist=None):
        raise NotImplementedError  # must be overridden

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

        handlers_list = list()
        for line in manifest_lines:
            line = re.sub(r'(?:\s+)?#.*(?:\n|$)', '', line)  # remove comments from the line
            if line.strip():  # ignore empty lines
                items = line.split()
                handlers_list.append((items[0], items[1:]))  # tuple: (module_to_import, [callbacks_list])

        return handlers_list

    @classmethod
    def load(cls, callbacks_dir, manifest_file=''):
        # try to load plugins from manifest file
        manifest_modules = cls._load_manifest(os.path.join(callbacks_dir, manifest_file))
        if manifest_modules:
            # build the base import path of the plugins/jobs directory
            target_dir_path = os.path.splitext(callbacks_dir)[0]
            target_dir_import_path_list = list()
            while target_dir_path:
                target_dir_path, tail = os.path.split(target_dir_path)
                target_dir_import_path_list.insert(0, tail)
            base_import_path = '.'.join(target_dir_import_path_list)

            for module, callbacks in manifest_modules:
                import_path = base_import_path + module
                # if the callbacks list is empty, import all the callbacks in the module
                valid_handlers = cls._fetch_valid_callbacks(
                    import_path,
                    callbacks_whitelist=callbacks if callbacks else None
                )
                if valid_handlers:
                    cls.list.extend(valid_handlers)
        else:
            # no manifest: load every module available in alphabetial order
            for path in sorted(Path(callbacks_dir).rglob('*.py')):
                file_path = os.path.splitext(str(path))[0]
                import_path = []
                while file_path:
                    file_path, tail = os.path.split(file_path)
                    import_path.insert(0, tail)

                import_path = '.'.join(import_path)
                valid_handlers = cls._fetch_valid_callbacks(import_path)
                cls.list.extend(valid_handlers)

        return len(cls.list)
