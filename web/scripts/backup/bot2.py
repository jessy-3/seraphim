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

stop_auto_message = False

async def auto_message(context, chat_id):
    count = 0
    while not stop_auto_message and count < 100:
        await context.bot.send_message(chat_id=chat_id, text=f"This is an automatic message. No. {count}")
        count += 1
        await asyncio.sleep(10)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global stop_auto_message
    stop_auto_message = False
    chat_id = update.effective_chat.id
    print(chat_id)
    await context.bot.send_message(chat_id=chat_id, text="I'm a bot, please talk to me!")
    asyncio.create_task(auto_message(context, chat_id))

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global stop_auto_message
    stop_auto_message = True
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="I'll stop sending automatic messages.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(update.message.text)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

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


if __name__ == '__main__':
    application = ApplicationBuilder().token('5196215968:AAEia96GXZVRtse1--ODdFH9vqmDgfm0jRM').build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    stop_handler = CommandHandler('stop', stop)
    application.add_handler(stop_handler)

    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    application.add_handler(echo_handler)

    # inline_caps_handler = InlineQueryHandler(inline_caps)   
    # application.add_handler(inline_caps_handler)
    
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    application.add_handler(unknown_handler)

    application.run_polling()

