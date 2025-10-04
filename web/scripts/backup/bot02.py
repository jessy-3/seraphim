from telegram.ext import Updater, CommandHandler, MessageHandler, filters
from telegram import ChatAction, MessageEntity, ParseMode

TOKEN = 'TOKEN'
WELCOME_MESSAGE = 'Welcome to my chat!'

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=WELCOME_MESSAGE)

def new_member(update, context):
    user = update.message.new_chat_members[0]
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Welcome, {user.first_name}!")

def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(filters.status_update.new_chat_members, new_member))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
