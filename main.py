import logging

import migrations
import bot
from config import config

logging.getLogger('migrations').setLevel(logging.WARNING)

migrations.main(config.sqlite.filename)

bot.main()
