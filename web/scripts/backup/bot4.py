import logging
import asyncio
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, Updater
import telegram.error
import redis
import threading

# to update telegram bot webhook to https as following
# https://api.telegram.org/bot<YOUR-BOT-TOKEN>/setWebhook?url=https://yourdomain.com/your-webhook-url

REDIS_HOST = "redis"  # Use your Redis host
REDIS_PORT = 6379  # Use your Redis port

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = "5196215968:AAEia96GXZVRtse1--ODdFH9vqmDgfm0jRM"
subscriptions = {}

async def listen_for_commands():
    print("Listening for commands...")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe("bot_commands")

    for message in pubsub.listen():
        if message["type"] == "message":
            received_message = message["data"].decode("utf-8")
            if " | " in received_message:
                command, payload = received_message.split(" | ", 1)
                print(f"Bot received command: {command} and payload: {payload}")
                # Handle the command and payload
            else:
                command = received_message
                print(f"Bot received command / message: {received_message}")
            await send_command_to_web(f"Bot received | {received_message}")
        await asyncio.sleep(1)  # Add a sleep to avoid high CPU usage


async def send_command_to_web(command: str):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    r.publish("web_commands", command)

async def send_command_to_go(command: str):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    r.publish("go_commands", command)

async def rcmsg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name
    chat_id = update.effective_chat.id
    message_parts = update.message.text.split("|")
    
    print(f"Redis msg received from {user_name}, {chat_id}")

    # Just welcome the user if no arguments are provided
    if len(message_parts) < 3:
        await context.bot.send_message(chat_id=chat_id, text=f"Hello, {user_name}! Invalid redis command!")
        return

    redis_channel = message_parts[1].lower()
    redis_command = message_parts[2].lower()
    if redis_channel == 'go':
        send_command_to_go(redis_command)
        await context.bot.send_message(chat_id=chat_id, text=f"Msg sent to go: {redis_command}")

    if redis_channel == 'web':  
        send_command_to_web(redis_command)
        await context.bot.send_message(chat_id=chat_id, text=f"Msg sent to go: {redis_command}")

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

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

async def shutdown():
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

async def run_bot():
    print("Running bot...")
    updater = Updater(TOKEN, use_context=True)
    # application = ApplicationBuilder().token(TOKEN).build()

    rcmsg_handler = CommandHandler('rcmsg', rcmsg)
    # application.add_handler(rcmsg_handler)
    updater.dispatcher.add_handler(rcmsg_handler)

    start_handler = CommandHandler('start', start)
    updater.dispatcher.add_handler(start_handler)

    stop_handler = CommandHandler('stop', stop)
    updater.dispatcher.add_handler(stop_handler)

    sub_handler = CommandHandler('sub', sub)
    updater.dispatcher.add_handler(sub_handler)

    unsub_handler = CommandHandler('unsub', unsub)
    updater.dispatcher.add_handler(unsub_handler)

    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    updater.dispatcher.add_handler(echo_handler)

    help_handler = CommandHandler('help', help)
    updater.dispatcher.add_handler(help_handler)   

    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    updater.dispatcher.add_handler(unknown_handler)

    try:
        await updater.start_polling()
    except telegram.error.Conflict as e:
        print(f"Error: {e.message}. Make sure that only one bot instance is running.")
    
    return updater

async def main():
    # Run both functions concurrently
    updater = await run_bot()
    await asyncio.gather(listen_for_commands())

    # Stop the bot
    await updater.stop()

if __name__ == '__main__':
    asyncio.run(main())