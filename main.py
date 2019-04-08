import logging

from utilities import l
from bot import main
from config import config


logger = logging.getLogger(__name__)
l.load_logging_config(config.logging.config, config.logging.filepath)


if __name__ == '__main__':
    main()
