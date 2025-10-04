import logging
import os
import redis
import asyncio
import json
from json import JSONDecodeError
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.utils import executor

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("listen_for_commands")
main_logger = logging.getLogger('main')

# to update telegram bot webhook to https as following
# https://api.telegram.org/bot<YOUR-BOT-TOKEN>/setWebhook?url=https://yourdomain.com/your-webhook-url

REDIS_HOST = "redis"  # Use your Redis host
REDIS_PORT = 6379  # Use your Redis port
SUBSCRIPTIONS_KEY = "subscriptions"

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

TOKEN = "5196215968:AAEia96GXZVRtse1--ODdFH9vqmDgfm0jRM"    # jessy3_bot
# TOKEN = "5801301439:AAEXatteWvGo6BeBx3MZ8JdE77a6jEClV9o"    # ismtv_bot
subscriptions = {}

def save_subscriptions(subscriptions):
    subscriptions_list = {k: list(v) for k, v in subscriptions.items()}
    subscriptions_json = json.dumps(subscriptions_list)
    r.set(SUBSCRIPTIONS_KEY, subscriptions_json)

def load_subscriptions():
    global subscriptions
    subscriptions_json = r.get(SUBSCRIPTIONS_KEY)
    if subscriptions_json:
        try:
            subscriptions_list = json.loads(subscriptions_json)
            subscriptions = {int(k): set(v) for k, v in subscriptions_list.items()}
        except json.JSONDecodeError:
            main_logger.info("Error: JSON data is not properly formatted. Returning an empty dictionary.")
            print("Error: JSON data is not properly formatted. Returning an empty dictionary.")
            subscriptions = {}
    else:
        subscriptions = {}

    
# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

async def send_command_to_web(command: str):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    r.publish("web_commands", command)

async def send_command_to_go(command: str):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    r.publish("go_commands", command)

async def listen_for_commands():
    print("Listening for commands...")
    logging.debug("Listening for commands...")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe("bot_commands")
    while True:
        message = await asyncio.to_thread(pubsub.get_message)
        if message and message["type"] == "message":
            received_message = message["data"].decode("utf-8")
            if "|" in received_message:
                command, payload = received_message.split("|", 1)
                command = command.strip()
                logger.info(f"Bot received command: '{command}' and payload: {payload}")
                # Handle the command and payload
                for chat_id in subscriptions:
                    if command in subscriptions[chat_id]:
                        await bot.send_message(chat_id=chat_id, text=payload)
            else:
                command = received_message
                print(f"Bot received command / message: {received_message}")
            await send_command_to_web(f"Bot received | {received_message}")
            logger.info(f"Received: {received_message}")
        await asyncio.sleep(1)  # Add a sleep to avoid high CPU usage


async def rcmsg(message: types.Message):
    user = message.from_user
    user_name = user.first_name
    chat_id = message.chat.id
    message_parts = message.text.split("|")
    
    print(f"Redis msg received from {user_name}, {chat_id}")

    # Just welcome the user if no arguments are provided
    if len(message_parts) < 3:
        await bot.send_message(chat_id=chat_id, text=f"Hello, {user_name}! Invalid redis command!")
        return

    redis_channel = message_parts[1].strip().lower()
    redis_command = message_parts[2].strip()
    if len(message_parts) > 3:
        redis_command += " | " + message_parts[3].strip()
    if len(message_parts) > 4:
        redis_command += " | " + message_parts[4].strip()

    if redis_channel == 'go':
        await send_command_to_go(redis_command)
        await bot.send_message(chat_id=chat_id, text=f"Msg sent to go: {redis_command}")

    if redis_channel == 'web':  
        await send_command_to_web(redis_command)
        await bot.send_message(chat_id=chat_id, text=f"Msg sent to web: {redis_command}")

async def start(message: types.Message):
    user = message.from_user
    user_name = user.first_name
    chat_id = message.chat.id
    await bot.send_message(chat_id=chat_id, text=f"Welcome, {user_name}! I'm a bot, please talk to me or use `/help`!")

async def stop(message: types.Message):
    chat_id = message.chat.id

    # Unsubscribe the user from all subscriptions
    if chat_id in subscriptions:
        del subscriptions[chat_id]
        save_subscriptions(subscriptions)  # Save the updated subscription data

    # Send a goodbye message
    await bot.send_message(chat_id=chat_id, text="Goodbye! I'll stop talking now. All your automated services have been removed.")

async def auto_message(chat_id, message_type):
    count = 0
    while chat_id in subscriptions and message_type in subscriptions.get(chat_id, set()) and count < 15:
        count += 1
        await bot.send_message(chat_id=chat_id, text=f"Automatic {message_type} message {count}")
        print(f"Automatic {message_type} message {count}")
        await asyncio.sleep(10)


async def sub(message: types.Message):
    user = message.from_user
    user_name = user.first_name
    chat_id = message.chat.id
    message_parts = message.text.split(" ")

    print(f"Welcome, {user_name}, {chat_id}")

    # If no arguments are provided, reply with the list of subscribed channels
    if len(message_parts) < 2:
        if chat_id in subscriptions:
            subscribed_channels = ', '.join(subscriptions[chat_id])
            await bot.send_message(chat_id=chat_id, text=f"Hello, {user_name}! You are subscribed to the following channels: {subscribed_channels}")
        else:
            await bot.send_message(chat_id=chat_id, text=f"Hello, {user_name}! No subscription. Please specify.")
        return

    message_type = message_parts[1].lower()

    if chat_id not in subscriptions:
        subscriptions[chat_id] = set()

    if message_type not in subscriptions[chat_id]:
        subscriptions[chat_id].add(message_type)
        save_subscriptions(subscriptions)  # Save the updated subscription data
        await bot.send_message(chat_id=chat_id, text=f"Subscribed to {message_type} messages.")
        # asyncio.create_task(auto_message(context, chat_id, message_type))
    else:
        await bot.send_message(chat_id=chat_id, text=f"You are already subscribed to {message_type} messages.")


async def unsub(message: types.Message):
    chat_id = message.chat.id
    message_parts = message.text.split(" ")

    if len(message_parts) < 2:
        await bot.send_message(chat_id=chat_id, text="Please specify the subscription type or use `/unsub all` to unsubscribe all subscriptions.")
        return

    message_type = message_parts[1].lower()

    if message_type == "all":
        if chat_id in subscriptions:
            del subscriptions[chat_id]
            await bot.send_message(chat_id=chat_id, text="Unsubscribed from all messages.")
        else:
            await bot.send_message(chat_id=chat_id, text="You are not subscribed to any messages.")
    else:
        if chat_id in subscriptions and message_type in subscriptions[chat_id]:
            subscriptions[chat_id].remove(message_type)
            if len(subscriptions[chat_id])==0:
                del subscriptions[chat_id] 
            await bot.send_message(chat_id=chat_id, text=f"Unsubscribed from {message_type} messages.")
        else:
            await bot.send_message(chat_id=chat_id, text=f"You are not subscribed to {message_type} messages.")
    save_subscriptions(subscriptions)  # Save the updated subscription data


async def echo(message: types.Message):
    print(message.text)
    await bot.send_message(chat_id=message.chat.id, text=message.text)

async def help(message: types.Message):
    chat_id = message.chat.id
    help_text = (
        "This is a help message for your bot. You can customize this text to provide information about your bot's features and available commands.\n\n"
        "Here are some available commands:\n"
        "/start - Start the bot and receive a welcome message.\n"
        "/stop - Stop the bot and unsubscribe from all subscriptions.\n"
        "/sub <message_type> - Subscribe to a specific message type.\n"
        "/unsub <message_type> - Unsubscribe from a specific message type.\n"
        "/help - Get this help message.\n"
    )
    await bot.send_message(chat_id=chat_id, text=help_text)

async def unknown(message: types.Message):
    await bot.send_message(chat_id=message.chat.id, text="Sorry, I didn't understand that command.")

async def shutdown(dp: Dispatcher):
    await bot.close()
    await dp.storage.close()
    await dp.storage.wait_closed()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

async def run_bot():
    print("Running bot...")
    # dp.message_handler(lambda message: message.text.lower() == 'hello')(hello)

    dp.register_message_handler(rcmsg, commands=['rcmsg'])

    dp.register_message_handler(start, commands=['start'])
    dp.register_message_handler(stop, commands=['stop'])

    dp.register_message_handler(sub, commands=['sub'])
    dp.register_message_handler(unsub, commands=['unsub'])

    dp.register_message_handler(echo, content_types=['text'], regexp="^((?!/).)*$")
    dp.register_message_handler(help, commands=['help'])
    dp.register_message_handler(unknown, commands=['unknown'])

    # Start the bot
    await dp.start_polling()

async def main():
    main_logger.info("Bot async main is running")
    load_subscriptions()
    try:
        # Run both functions concurrently
        await asyncio.gather(run_bot(), listen_for_commands())
    finally:
        print("Shutting down bot...")
        await shutdown(dp)
        print("Bot stopped.")

if __name__ == '__main__':
    asyncio.run(main())
    pass