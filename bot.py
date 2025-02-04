import logging
import sys
import os
import signal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, filters

# Configure logging
logging.basicConfig(
    stream=sys.stdout,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
MINI_APP_URL = "https://make-ton-telegram-mini-app-1.vercel.app/"
WELCOME_IMAGE_PATH = 'preview.png'

# State constants for ConversationHandler
PASSWORD, LOCATION, TIME, EXTRA_INFO, CONFIRMATION = range(5)

# Set a predefined password
GAME_CREATION_PASSWORD = "12345"

# Dictionary to store ongoing game details
active_games = {}

# Token hardcoded directly in the code
TOKEN = '7675127420:AAFbt7343zQWIBJ9eiwNxpo46yf6DHGf1Kg'

# Message texts
WELCOME_MESSAGE = (
    "👋 Welcome to my Demo Bot!\n\n"
    "This bot demonstrates basic Telegram bot functionality "
    "and integration with Telegram Mini Apps.\n\n"
    "🔍 Features:\n"
    "- Basic command handling\n"
    "- Inline keyboard integration\n"
    "- Mini App integration\n\n"
    "Click the button below to open my Mini App!"
)

HELP_MESSAGE = (
    "🤖 Available Commands:\n\n"
    "/start - Start the bot and see welcome message\n"
    "/help - Show this help message\n"
    "/info - Get information about the bot\n"
    "/contact - Get contact information\n"
    "/about - Learn more about the project"
)

INFO_MESSAGE = (
    "ℹ️ Bot Information\n\n"
    "This is a demo bot showing basic Telegram bot capabilities "
    "and integration with Mini Apps. It's built using python-telegram-bot "
    "library and serves as an educational example."
)

CONTACT_MESSAGE = (
    "📞 Contact Information\n\n"
    "Website: https://nikandr.com\n"
    "Telegram: @nikandr_s\n"
    "Email: nikandr.dev@gmail.com\n"
    "GitHub: https://github.com/nikandr-surkov"
)

ABOUT_MESSAGE = (
    "🔍 About This Project\n\n"
    "This bot was created as a demonstration of Telegram bot development "
    "using Python. It showcases various bot features including:\n\n"
    "• Command handling\n"
    "• Inline keyboards\n"
    "• Mini App integration\n"
    "• Image sharing\n"
    "• Interactive responses"
)


async def start(update: Update, context: CallbackContext):
    logger.info(f"User {update.effective_user.id} started the bot")
    keyboard = [
        [InlineKeyboardButton(
            "Open Mini App",
            web_app={"url": MINI_APP_URL}
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        with open(WELCOME_IMAGE_PATH, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=WELCOME_MESSAGE,
                reply_markup=reply_markup
            )
    except FileNotFoundError:
        logger.error(f"Welcome image not found at {WELCOME_IMAGE_PATH}")
        await update.message.reply_text(
            WELCOME_MESSAGE,
            reply_markup=reply_markup
        )


async def help(update: Update, context: CallbackContext):
    logger.info(f"User {update.effective_user.id} requested help")
    await update.message.reply_text(HELP_MESSAGE)


async def info(update: Update, context: CallbackContext):
    logger.info(f"User {update.effective_user.id} requested info")
    await update.message.reply_text(INFO_MESSAGE)


async def contact(update: Update, context: CallbackContext):
    logger.info(f"User {update.effective_user.id} requested contact info")
    await update.message.reply_text(CONTACT_MESSAGE)


async def about(update: Update, context: CallbackContext):
    logger.info(f"User {update.effective_user.id} requested about info")
    await update.message.reply_text(ABOUT_MESSAGE)




async def oyun_yarat(update: Update, context: CallbackContext):
    """Starts the game creation process by requesting a password."""
    await update.message.reply_text("🔑 Oyunu yaratmaq üçün şifrə daxil edin:")
    return PASSWORD

async def check_password(update: Update, context: CallbackContext):
    """Verifies the entered password."""
    if update.message.text != GAME_CREATION_PASSWORD:
        await update.message.reply_text("❌ Şifrə yalnışdır! Yenidən cəhd edin.")
        return ConversationHandler.END
    
    await update.message.reply_text("📍 Oyun keçiriləcək məkanı daxil edin:")
    return LOCATION

async def set_location(update: Update, context: CallbackContext):
    """Sets the game location."""
    context.user_data["location"] = update.message.text
    await update.message.reply_text("⏰ Oyun vaxtını daxil edin:")
    return TIME

async def set_time(update: Update, context: CallbackContext):
    """Sets the game time."""
    context.user_data["time"] = update.message.text
    await update.message.reply_text("📄 Əlavə məlumatları daxil edin:")
    return EXTRA_INFO

async def set_extra_info(update: Update, context: CallbackContext):
    """Sets additional game details and confirms creation."""
    context.user_data["extra_info"] = update.message.text
    user_id = update.effective_user.id

    # Store the game details
    active_games[user_id] = {
        "location": context.user_data["location"],
        "time": context.user_data["time"],
        "extra_info": context.user_data["extra_info"],
        "creator": user_id
    }

    keyboard = [[InlineKeyboardButton("❌ SİL", callback_data=f"delete_game_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    game_info = (
        f"✅ **Oyun yaradıldı!**\n\n"
        f"📍 **Məkan:** {context.user_data['location']}\n"
        f"⏰ **Vaxt:** {context.user_data['time']}\n"
        f"📄 **Əlavə məlumat:** {context.user_data['extra_info']}\n"
    )

    await update.message.reply_text(game_info, reply_markup=reply_markup)
    return ConversationHandler.END

async def delete_game(update: Update, context: CallbackContext):
    """Deletes the created game if the user is the creator."""
    query = update.callback_query
    user_id = query.from_user.id

    if user_id in active_games:
        del active_games[user_id]
        await query.message.edit_text("🗑️ Oyun uğurla silindi!")
    else:
        await query.answer("Bu oyunu silməyə icazəniz yoxdur!", show_alert=True)

async def cancel(update: Update, context: CallbackContext):
    """Cancels the game creation process."""
    await update.message.reply_text("🚫 Oyun yaradılması ləğv edildi.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Define the conversation handler
game_handler = ConversationHandler(
    entry_points=[CommandHandler("oyunyarat", oyun_yarat)],
    states={
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
        LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_location)],
        TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_time)],
        EXTRA_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_extra_info)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

# Add handlers to the bot
application.add_handler(game_handler)
application.add_handler(CallbackQueryHandler(delete_game, pattern=r"delete_game_\d+"))




async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Sorry, something went wrong. Please try again later."
        )


def signal_handler(signum, frame):
    logger.info('Signal received, shutting down...')
    exit(0)


def main():
    # Initialize bot
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("contact", contact))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("oyun_yarat", oyun_yarat))

    # Add error handler
    application.add_error_handler(error_handler)

    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
