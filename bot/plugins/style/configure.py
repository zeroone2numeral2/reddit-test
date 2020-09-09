import logging
import re

from telegram import Update
from telegram.ext import MessageHandler, CommandHandler, CallbackContext
from telegram.ext import Filters
from telegram.ext import ConversationHandler
from peewee import IntegrityError

from bot import mainbot
from bot.conversation import Status
from database.models import Subreddit
from database.models import Style
from database.queries import styles
from bot.markups import Keyboard
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

STYLE_SELECTED_TEXT = """Now you can configure <code>{s.name}</code>.
You can use the following commands: /info, /remove, /default, /subreddits, /rename

Pass any field to get its current value, or a field followed by the new value to change it.

Just send the field with the new value. Use /exit to exit the configuration, or /style to change the \
style to configure"""


@d.restricted
@d.failwithmessage
@d.logconversation
def on_newstyle_command(update: Update, context: CallbackContext):
    logger.info('/newstyle command')

    if not context.args:
        update.message.reply_text('Please provide the style name')
        return ConversationHandler.END

    style_name = u.to_ascii(context.args[0].lower())
    if not style_name:
        update.message.reply_text('Invalid name')
        return ConversationHandler.END

    try:
        style = Style.create(
            name=style_name,
            created=u.now(),
            updated=u.now()
        )
    except IntegrityError:
        update.message.reply_html('The style <code>{}</code> already exists'.format(style_name))
        return ConversationHandler.END

    update.message.reply_html('Style <code>{}</code> created'.format(style_name))

    text = STYLE_SELECTED_TEXT.format(s=style)
    update.message.reply_html(text, disable_web_page_preview=True, reply_markup=Keyboard.REMOVE)

    context.user_data['data'] = dict()
    context.user_data['data']['style'] = style

    return Status.WAITING_STYLE_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_style
def on_rename_command(update: Update, context: CallbackContext, style: Style):
    logger.info('/rename command')

    if not context.args:
        update.message.reply_text('Please provide the new style name')
        return Status.WAITING_STYLE_CONFIG_ACTION

    new_name = u.to_ascii(context.args[0].lower())
    if not new_name:
        update.message.reply_text('Invalid name')
        return Status.WAITING_STYLE_CONFIG_ACTION

    try:
        style.name = new_name
        style.save()
    except IntegrityError:
        update.message.reply_html('There\'s already a style named <code>{}</code>'.format(new_name))
        return Status.WAITING_STYLE_CONFIG_ACTION

    update.message.reply_html('Style renamed to <code>{}</code>'.format(new_name))

    return Status.WAITING_STYLE_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
def on_style_command(update: Update, context: CallbackContext):
    logger.debug('/style: selecting style, text: %s', update.message.text)

    name_filter = context.args[0].lower() if context.args else None

    styles: [Style] = Style.get_list(name_filter=name_filter)
    if not styles:
        update.message.reply_text('Cannot find any style (filter: {})'.format(name_filter))
        return ConversationHandler.END

    buttons_list = [style.name for style in styles]
    reply_markup = Keyboard.from_list(buttons_list)

    update.message.reply_text('Select the style (or /cancel):', reply_markup=reply_markup)

    return Status.STYLE_SELECT


@d.restricted
@d.failwithmessage
@d.logconversation
def on_exit_command(update: Update, context: CallbackContext):
    logger.info('/exit command')

    context.user_data.pop('data', None)

    update.message.reply_html('Exited configuration', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.logconversation
def on_cancel_command(update: Update, context: CallbackContext):
    logger.info('/cancel command')

    if context.user_data.get('data', None) and context.user_data['data'].get('style', None):
        text = 'Operation canceled, back to style configuration'
        step_to_return = Status.WAITING_STYLE_CONFIG_ACTION
    else:
        # it might be that the user uses /style and then /cancel before selecting one. If we weren't already
        # inside a conversation, we should answer in a different way
        text = 'Operation canceled'
        step_to_return = ConversationHandler.END

    update.message.reply_html(text, reply_markup=Keyboard.REMOVE)

    return step_to_return


@d.restricted
@d.failwithmessage
@d.logconversation
def on_fake_cancel_command(update: Update, context: CallbackContext):
    logger.info('fake /cancel command')

    update.message.reply_html(
        'There is no operation to be canceled. Use /exit to exit the configuration mode',
        reply_markup=Keyboard.REMOVE
    )

    return Status.WAITING_STYLE_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
def on_timeout(update: Update, context: CallbackContext):
    logger.debug('conversation timeout')

    context.user_data.pop('data', None)

    update.message.reply_text('Timeout: exited styles configuration', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.logconversation
def on_style_selected(update: Update, context: CallbackContext):
    logger.info('/style command: style selected (%s)', update.message.text)

    style = Style.by_name(update.message.text)
    if not style:
        update.message.reply_text('No style found for "{}", try again or /cancel'.format(update.message.text))
        return Status.STYLE_SELECT

    context.user_data['data'] = dict()
    context.user_data['data']['style'] = style

    text = STYLE_SELECTED_TEXT.format(s=style)
    update.message.reply_html(text, disable_web_page_preview=True, reply_markup=Keyboard.REMOVE)

    return Status.WAITING_STYLE_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_style
def on_remove_command(update: Update, context: CallbackContext, style: Style):
    logger.info('/remove command')

    if style.default:
        update.message.reply_text('You cannot delete the default style')
        return Status.WAITING_STYLE_CONFIG_ACTION

    if styles.is_used(style):
        # for some reason sometime external keys checks don't work
        update.message.reply_text('You cannot delete a style which is used by some subreddits (see /subreddits)')
        return Status.WAITING_STYLE_CONFIG_ACTION

    try:
        style.delete_instance()
    except IntegrityError:
        update.message.reply_text('You cannot delete a style which is used by some subreddits (see /subreddits)')
        return Status.WAITING_STYLE_CONFIG_ACTION

    update.message.reply_html('<code>{s.name}</code> has gone, you have also exited the styles configuration'.format(
        s=style
    ))

    context.user_data.pop('data', None)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_style
def on_makedefault_command(update: Update, _, style: Style):
    logger.info('/default command')

    if style.default:
        update.message.reply_text('This style is already the default style')
        return Status.WAITING_STYLE_CONFIG_ACTION

    style.make_default()
    style.update_time(u.now())

    update.message.reply_html('<code>{s.name}</code> is now the default style'.format(s=style))

    return Status.WAITING_STYLE_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_style
def on_subreddits_command(update: Update, _, style: Style):
    logger.info('/subreddits command')

    subs = Subreddit.using_style(style)
    if not subs:
        update.message.reply_text('No subreddit is using this style')
        return Status.WAITING_STYLE_CONFIG_ACTION

    lines = ['{s.name} ({s.id})'.format(s=s) for s in subs]
    text = '<code>{}</code>'.format('\n'.join(lines))

    update.message.reply_html(text)

    return Status.WAITING_STYLE_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_style
def on_info_command(update: Update, _, style: Style):
    logger.info('/info command')

    text = u.model_dict(style, plain_formatted_string=True)
    update.message.reply_html(text, disable_web_page_preview=True)

    return Status.WAITING_STYLE_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_style
def on_entry_change(update: Update, _, style: Style):
    logger.info('changed style property: %s', update.message.text)

    logger.info('style_name: %s', style.name)

    # just return the value if only one word is passed
    if re.search(r'^\w+$', update.message.text, re.I & re.M):
        setting = update.message.text.lower()
        style_dict = style.to_dict()

        try:
            style_dict[setting]
        except KeyError:
            update.message.reply_text('Cannot find field "{}" in the database row'.format(setting))
            return Status.WAITING_STYLE_CONFIG_ACTION

        value = getattr(style, setting)

        update.message.reply_html('Current value of <code>{}</code>:'.format(setting))
        update.message.reply_html('<code>{}</code>'.format(u.escape(str(value))))

        return Status.WAITING_STYLE_CONFIG_ACTION

    # extract values
    match = re.search(r'^(\w+)\s+((?:.|\s)+)$', update.message.text, re.I & re.M)
    if not match:
        update.message.reply_html('Use the following format: <code>[db field] [new value]</code>')
        return Status.WAITING_STYLE_CONFIG_ACTION

    key = match.group(1)
    value = match.group(2)
    logger.info('key: %s; value: %s', key, value)

    if not style.field_exists(key):
        update.message.reply_html('Cannot find field <code>{}</code> in the database row'.format(key))
        return Status.WAITING_STYLE_CONFIG_ACTION

    value = u.string_to_python_val(value)
    logger.info('value after validation and conversion: %s', value)

    try:
        setattr(style, key, value)
        style.save()
    except Exception as e:
        logger.error('error while setting subreddit object property (%s, %s): %s', key, str(value), str(e), exc_info=True)
        update.message.reply_text('Error while setting the property: {}'.format(str(e)))
        return Status.WAITING_STYLE_CONFIG_ACTION

    new_value = getattr(style, key)

    style.update_time(u.now())

    update.message.reply_html('Done, new value of <code>{setting}</code>:\n<code>{new_value}</code>\n\n<b>Value type</b>: <code>{input_type}</code>'.format(
        setting=key,
        new_value=u.escape(str(new_value)),
        input_type=u.escape(str(type(value).__name__))
    ))

    return Status.WAITING_STYLE_CONFIG_ACTION


mainbot.add_handler(ConversationHandler(
    entry_points=[
        CommandHandler(['style'], on_style_command),
        CommandHandler(['newstyle'], on_newstyle_command),
    ],
    states={
        Status.STYLE_SELECT: [
            MessageHandler(Filters.text & ~Filters.command, on_style_selected),
            CommandHandler(['cancel'], on_cancel_command)
        ],
        Status.WAITING_STYLE_CONFIG_ACTION: [
            CommandHandler(['remove', 'rem'], on_remove_command),
            CommandHandler(['default', 'makedefault'], on_makedefault_command),
            CommandHandler(['subreddits'], on_subreddits_command),
            CommandHandler(['info'], on_info_command),
            CommandHandler(['style'], on_style_command),
            CommandHandler(['newstyle'], on_newstyle_command),
            CommandHandler(['rename'], on_rename_command),
            CommandHandler(['cancel'], on_fake_cancel_command),
            MessageHandler(Filters.text & ~Filters.command, on_entry_change),
        ],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.all, on_timeout)],
    },
    fallbacks=[CommandHandler(['exit'], on_exit_command)],
    conversation_timeout=15 * 60
))
