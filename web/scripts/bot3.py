import logging
import asyncio
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
# from telegram import InlineQueryResultArticle, InputTextMessageContent
# from telegram.ext import InlineQueryHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

subscriptions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text=f"Welcome, {user_name}! I'm a bot, please talk to me or use `/help`!")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Unsubscribe the user from all subscriptions
    if chat_id in subscriptions:
        del subscriptions[chat_id]

    # Send a goodbye message
    await context.bot.send_message(chat_id=chat_id, text="Goodbye! I'll stop talking now. All your automated services have been removed.")

async def auto_message(context, chat_id, message_type):
    count = 0
    while chat_id in subscriptions and message_type in subscriptions.get(chat_id, set()) and count < 15:
        count += 1
        await context.bot.send_message(chat_id=chat_id, text=f"Automatic {message_type} message {count}")
        print(f"Automatic {message_type} message {count}")
        await asyncio.sleep(10)

async def sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name
    chat_id = update.effective_chat.id
    message_parts = update.message.text.split(" ")
    
    print(f"Welcome, {user_name}, {chat_id}")

    # Just welcome the user if no arguments are provided
    if len(message_parts) < 2:
        await context.bot.send_message(chat_id=chat_id, text=f"Hello, {user_name}! Please specify the subscription type!")
        return

    message_type = message_parts[1].lower()

    if chat_id not in subscriptions:
        subscriptions[chat_id] = set()

    if message_type not in subscriptions[chat_id]:
        subscriptions[chat_id].add(message_type)
        await context.bot.send_message(chat_id=chat_id, text=f"Subscribed to {message_type} messages.")
        asyncio.create_task(auto_message(context, chat_id, message_type))
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"You are already subscribed to {message_type} messages.")

async def unsub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message_parts = update.message.text.split(" ")

    if len(message_parts) < 2:
        await context.bot.send_message(chat_id=chat_id, text="Please specify the subscription type or use `/unsub all` to unsubscribe all subscriptions.")
        return

    message_type = message_parts[1].lower()

    if message_type == "all":
        if chat_id in subscriptions:
            del subscriptions[chat_id]
            await context.bot.send_message(chat_id=chat_id, text="Unsubscribed from all messages.")
        else:
            await context.bot.send_message(chat_id=chat_id, text="You are not subscribed to any messages.")
    else:
        if chat_id in subscriptions and message_type in subscriptions[chat_id]:
            subscriptions[chat_id].remove(message_type)
            await context.bot.send_message(chat_id=chat_id, text=f"Unsubscribed from {message_type} messages.")
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"You are not subscribed to {message_type} messages.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(update.message.text)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    help_text = (
        "This is a help message for your bot. You can customize this text to provide information about your bot's features and available commands.\n\n"
        "Here are some available commands:\n"
        "/start - Start the bot and receive a welcome message.\n"
        "/stop - Stop the bot and unsubscribe from all subscriptions.\n"
        "/sub <message_type> - Subscribe to a specific message type.\n"
        "/unsub <message_type> - Unsubscribe from a specific message type.\n"
        "/help - Get this help message.\n"
    )
    await context.bot.send_message(chat_id=chat_id, text=help_text)

# async def inline_caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.inline_query.query
#     if not query:
#         return
#     results = []
#     results.append(
#         InlineQueryResultArticle(
#             id=query.upper(),
#             title='Caps',
#             input_message_content=InputTextMessageContent(query.upper())
#         )
#     )
#     await context.bot.answer_inline_query(update.inline_query.id, results)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

def activate_bot(telegram_token):
    application = ApplicationBuilder().token(telegram_token).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    stop_handler = CommandHandler('stop', stop)
    application.add_handler(stop_handler)

    sub_handler = CommandHandler('sub', sub)
    application.add_handler(sub_handler)

    unsub_handler = CommandHandler('unsub', unsub)
    application.add_handler(unsub_handler)

    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    application.add_handler(echo_handler)

    help_handler = CommandHandler('help', help)
    application.add_handler(help_handler)   

    # inline_caps_handler = InlineQueryHandler(inline_caps)   
    # application.add_handler(inline_caps_handler)
    
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    application.add_handler(unknown_handler)

    application.run_polling()

if __name__ == '__main__':
    activate_bot('5196215968:AAEia96GXZVRtse1--ODdFH9vqmDgfm0jRM')
