import datetime
import logging
import os
import subprocess

from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def update_ytdl(update, context: CallbackContext):
    logger.info('/updateytdl command')

    pip_versions = (
        'pip',
        'pip3',
        'pip3.5',
        'pip3.6'
    )

    dt_filename = datetime.datetime.now().strftime('%Y%m%d_%H%M')

    for pip_v in pip_versions:
        cmd = './venv/bin/{} {}'.format(pip_v, ' install -U youtube_dl')
        logger.info('executing cmd: %s', cmd)

        update.message.reply_text('Executing: {}'.format(cmd))

        stdout_filepath = os.path.join('logs/youtubedl', 'updateytdl_stdout_{}_{}.log'.format(dt_filename, pip_v))
        stderr_filepath = os.path.join('logs/youtubedl', 'updateytdl_stderr_{}_{}.log'.format(dt_filename, pip_v))

        stdout_file = open(stdout_filepath, 'wb')
        stderr_file = open(stderr_filepath, 'wb')

        sp = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=stderr_file)
        try:
            outs, errs = sp.communicate(timeout=120)
            update.message.reply_text('out: {}\n\nerrors: {}'.format(outs, errs))
        except subprocess.TimeoutExpired:
            logger.error(
                'subprocess.TimeoutExpired (%d seconds) error during update youtube_dl command execution (see %s, %s)',
                120,
                str(stdout_filepath),
                str(stderr_filepath)
            )

            sp.kill()
            stdout_file.close()
            stderr_file.close()

        stdout_file.close()
        stderr_file.close()

    update.message.reply_text('Done')


mainbot.add_handler(CommandHandler(['updateytdl'], update_ytdl))
