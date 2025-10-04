import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, filters

# Replace with your own bot token and chat ID
TOKEN = 'TOKEN'
USER_CHAT_ID = '970094463'

# Define a function to handle incoming messages
def handle_message(update, context):
    message = update.message
    chat_id = message.chat_id
    text = message.text
    print(f'Received message from chat ID {chat_id}: {text}')
    context.bot.send_message(chat_id=chat_id, text=f'Your chat ID is {chat_id}')

# Set up the Telegram bot
bot = telegram.Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Add a handler to handle incoming messages
dispatcher.add_handler(MessageHandler(filters.text, handle_message))

# Start the bot
updater.start_polling()

# Send a test message to the bot and check if the chat ID is echoed back
bot.send_message(chat_id=USER_CHAT_ID, text='Hello, bot!')
