import logging
import re
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class Registration:
    list = []

    @staticmethod
    def fetch_valid_callbacks(import_path, callbacks_whitelist=None):
        raise NotImplementedError  # questa deve essere sovrascritta

    @staticmethod
    def load_manifest(manifest_path):
        if not manifest_path:
            return

        try:
            with open(manifest_path, 'r') as f:
                manifest_str = f.read()
        except FileNotFoundError:
            logger.info('manifest "%s" not found', manifest_path)
            return

        if not manifest_str.strip():
            return

        manifest_str = manifest_str.replace('\r\n', '\n')
        manifest_lines = manifest_str.split('\n')

        handlers_list = list()
        for line in manifest_lines:
            line = re.sub(r'(?:\s+)?#.*(?:\n|$)', '', line)  # rimuovi commenti dalla riga
            if line.strip():  # ignora righe con spazi vuoti
                items = line.split()
                handlers_list.append((items[0], items[1:]))  # tupla: (modulo_da_importare, [lista_callback])

        return handlers_list

    @classmethod
    def load(cls, callbacks_dir, manifest_file=''):
        # prova a caricare plugins dal manifest
        manifest_modules = cls.load_manifest(os.path.join(callbacks_dir, manifest_file))
        if manifest_modules:
            # costruisci path import base della cartella dei plugins/jobs
            target_dir_path = os.path.splitext(callbacks_dir)[0]
            target_dir_import_path_list = list()
            while target_dir_path:
                target_dir_path, tail = os.path.split(target_dir_path)
                target_dir_import_path_list.insert(0, tail)
            base_import_path = '.'.join(target_dir_import_path_list)

            for module, callbacks in manifest_modules:
                import_path = base_import_path + module
                # se la lista delle callbacks è vuota, importa tutte le callback nel modulo
                valid_handlers = cls.fetch_valid_callbacks(
                    import_path,
                    callbacks_whitelist=callbacks if callbacks else None
                )
                if valid_handlers:
                    cls.list.extend(valid_handlers)
        else:
            # nessun manifest: carica tutti i moduli disponibili in ordine alfabetico
            for path in sorted(Path(callbacks_dir).rglob('*.py')):
                file_path = os.path.splitext(str(path))[0]
                import_path = []
                while file_path:
                    file_path, tail = os.path.split(file_path)
                    import_path.insert(0, tail)

                import_path = '.'.join(import_path)
                valid_handlers = cls.fetch_valid_callbacks(import_path)
                cls.list.extend(valid_handlers)

        return len(cls.list)
