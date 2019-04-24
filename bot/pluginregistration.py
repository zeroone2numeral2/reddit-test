import logging
from importlib import import_module

from telegram.ext import Handler

from .registration import Registration

logger = logging.getLogger('plugins')


class Plugins(Registration):
    list = []

    @staticmethod
    def _fetch_valid_callbacks(import_path, callbacks_whitelist=None):
        valid_handlers = list()

        try:
            module = import_module(import_path)
        except Exception as e:
            logger.warning('could not import module %s: %s', import_path, str(e))
            return

        names_list = list(vars(module).keys()) if callbacks_whitelist is None else callbacks_whitelist
        # logger.debug('functions to test from %s: %s', import_path, ', '.join(names_list))
        for name in names_list:
            try:
                # we *try* to import the name because we are not sure the module has that attribute (eg. if a callbacks
                # whitelist is passed, we are not sure all the calback functions are present in the module
                handlers_list = getattr(module, name)  # @Plugin.add() generates a list (decorators stack)
            except AttributeError:
                logger.warning('AttributeError: could not import "%s" from module %s', name, import_path)
                continue

            if isinstance(handlers_list, list):
                # filter out list items that are not a tuple of length 2, otherwise the loop will crash
                handlers_list = [i for i in handlers_list if isinstance(i, tuple) and len(i) == 2]
                for handler, group in handlers_list:
                    if isinstance(handler, Handler) and isinstance(group, int):
                        logger.debug('%s <%s.%s> will be loaded in group %d', type(handler).__name__, import_path, name, group)
                        valid_handlers.append((handler, group))
                    else:
                        logger.debug('function %s.%s(%s) skipped because not instance of Handler', import_path,
                                     type(handler).__name__, name)

        return valid_handlers

    @staticmethod
    def add(handler, group=0, *args, **kwargs):
        def decorator(func):
            return_list = list()
            if isinstance(func, list):
                # we use a list to support stacking of @Plugins.add() on the same callback function
                return_list.extend(func)

                # func[0] is the first list item, func[0][0] if the first tuple item (that is,
                # an instance of an handler)
                func = func[0][0].callback  # get the callback, it's the same for every item in the list

            logger.debug('converting function <%s> to %s (decorators stack depth: %d)', func.__name__, handler.__name__, len(return_list))

            ptb_handler = handler(callback=func, *args, **kwargs)
            return_list.append((ptb_handler, group))

            return return_list

        return decorator

    @classmethod
    def add_conversation_hanlder(cls, conv_handler, group=0):
        def decorator(dummy_func):
            return_list = list()

            logger.debug('adding to cls.list ConversationHandler <%s> in group %d', dummy_func.__name__, group)

            return_list.append((conv_handler, group))

            return return_list

        return decorator

    @classmethod
    def register(cls):
        if not cls.dispatcher:
            raise ValueError('a dispatcher must be set first with Plugins.hook()')

        for handler, group in cls.list:
            cls.dispatcher.add_handler(handler, group)
