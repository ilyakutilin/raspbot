from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from raspbot.bot.constants import states, text


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        text=f"{text.GREETING}\n\n{text.INPUT_DEPARTURE_STATION}",
    )
    return states.DEPARTURE_STATION


async def select_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(text=text.INPUT_DESTINATION_STATION)
    return states.DESTINATION_STATION


async def give_closest_trains(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(text="And here goes the list of the closest trains")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Bye! I hope we can talk again some day.")
    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start_command)],
    states={
        states.DEPARTURE_STATION: [MessageHandler(filters.TEXT, select_destination)],
        states.DESTINATION_STATION: [MessageHandler(filters.TEXT, give_closest_trains)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
