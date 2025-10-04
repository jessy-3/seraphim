import logging
import os
import time

from telegram.ext import Updater, CommandHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

PORT = int(os.environ.get('PORT', '8443'))


def start(update, context):
    """Sends a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(update, context):
    """Sends a message when the command /help is issued."""
    update.message.reply_text('Help!')


def start_auto(update, context):
    """Sends a message when the command /start_auto is issued."""
    n = 0
    while n < 6:
        time.sleep(10)
        update.message.reply_text(f'Auto message! {n}')
        n += 1


def error(update, context):
    """Logs Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    TOKEN = 'TOKEN'
    APP_NAME = 'https://dev.ismartinfo.net/' 

    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("start_auto", start_auto))

    # log all errors
    dp.add_error_handler(error)
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=APP_NAME + TOKEN)
    updater.idle()


if __name__ == '__main__':
    main()