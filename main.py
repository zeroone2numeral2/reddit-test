import logging
import logging.config
import json

from bot import main
from config import config


def load_logging_config(file_path, logfile):
    with open(file_path, 'r') as f:
        logging_config = json.load(f)
    logging_config['handlers']['file']['filename'] = logfile
    logging.config.dictConfig(logging_config)


logger = logging.getLogger(__name__)
load_logging_config(config.logging.config, config.logging.filepath)


if __name__ == '__main__':
    main()
