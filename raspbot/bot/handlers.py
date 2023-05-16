from telegram import Update
from telegram.ext import ContextTypes

import raspbot.bot.text as msg


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{msg.GREETING}, {update.message.chat.first_name}! {msg.INPUT_CITY}",
    )
