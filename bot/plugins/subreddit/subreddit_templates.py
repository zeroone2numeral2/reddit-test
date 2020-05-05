import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from const import DEFAULT_TEMPLATES
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

SUBREDDIT_SELECT = 0


@d.restricted
@d.failwithmessage
def get_templates(update: Update, _):
    logger.info('/templates command')

    strings = list()
    for i, template in enumerate(DEFAULT_TEMPLATES):
        strings.append('Template #{}:\n<code>{}</code>'.format(i + 1, template))

    for text in u.split_text(strings, join_by='\n\n'):
        update.message.reply_html(text)


@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def sub_set_template(update: Update, context: CallbackContext, subreddit=None):
    logger.info('/setchannelicon command')

    if len(context.args) < 1:
        update.message.reply_text('Pass a template index (1-{}), or see them using /templates'.format(len(DEFAULT_TEMPLATES)))
        return

    try:
        template = DEFAULT_TEMPLATES[int(context.args[0]) - 1]
    except (IndexError, ValueError):
        update.message.reply_text('Accepted values: 1-{}'.format(len(DEFAULT_TEMPLATES)))
        return

    subreddit.template = template
    subreddit.save()

    update.message.reply_text('Template updated:')
    update.message.reply_html('<code>{}</code>'.format(template))


mainbot.add_handler(CommandHandler(['templates'], get_templates))
mainbot.add_handler(CommandHandler(['settemplate'], sub_set_template))
