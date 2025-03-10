import logging
import threading
import time
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import buy, sell
import json
import dontshare as d

# Configure logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO)
# logger = logging.getLogger(__name__)

# Global variables to manage the bot state
running = False
buy_running=False


def buy_logic():
    while buy_running:
        print("buying...")
        result = buy.main()  
        if isinstance(
                result,
            (dict, list, str, int, float)):  # Check if result is serializable
            result_type = "🎁🎁🎁 " + result[0]["type"] + " 🎁🎁🎁"
            result_transaction = result[0]["transaction"]
            result_transaction_url = result[0]["transaction_url"]
            if result != "null":
                asyncio.run_coroutine_threadsafe(send_message(result_type + '\n' + result_transaction_url),
                                                 loop)
        time.sleep(28)  # Wait for 38 seconds


def sell_logic():
    while running:
        print("selling...")
        result = sell.main() 
        time.sleep(5)


async def send_message(message):
    # Replace with your chat_id
    chat_id = d.chat_id
    await application.bot.send_message(chat_id=chat_id, text=message)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global running
    global buy_running
    global loop
    running = True
    buy_running = True
    await update.message.reply_text('Bot started!')

    # Start the buying and selling threads
    threading.Thread(target=buy_logic).start()
    threading.Thread(target=sell_logic).start()


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global buy_running
    buy_running = False
    await update.message.reply_text('Bot stopped!')


def main():
    global application
    global loop
    # Replace 'YOUR_TOKEN' with your actual bot token
    application = ApplicationBuilder().token(
        d.BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))

    # Start the event loop
    loop = asyncio.get_event_loop()

    # Start polling
    application.run_polling()


if __name__ == '__main__':
    main()
