import logging

from .models import create_tables

logger = logging.getLogger(__name__)


logger.info('initializing database...')
create_tables()
