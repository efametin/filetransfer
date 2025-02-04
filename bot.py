import logging
import sys
import os
import signal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, filters, CallbackQueryHandler

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

# State constants for ConversationHandler
PASSWORD, LOCATION, TIME, EXTRA_INFO = range(4)

# Set a predefined password
GAME_CREATION_PASSWORD = "12345"

# Dictionary to store ongoing game details
active_games = {}
vote_data = {}

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

async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Sorry, something went wrong. Please try again later."
        )


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
        "creator": user_id,
        "participants": set()
    }

    keyboard = [
    [InlineKeyboardButton("❌ SİL", callback_data=f"delete_game_{user_id}")],
    [InlineKeyboardButton("🏁 Oyunu Bitir", callback_data=f"finish_game_{user_id}")],
    [InlineKeyboardButton("✅ OYUNA GƏLİRƏM", callback_data=f"join_game_{user_id}")],
    [InlineKeyboardButton("❌ GƏLƏ BİLMİRƏM", callback_data=f"leave_game_{user_id}")]
]


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

async def oyun(update: Update, context: CallbackContext):
    """Shows the details of the currently active game."""
    user_id = update.effective_user.id

    if user_id not in active_games:
        await update.message.reply_text("❌ Hazırda yaradılmış oyun yoxdur.")
        return

    game = active_games[user_id]
    game_info = (
        f"🎮 **Aktiv Oyun:**\n\n"
        f"📍 **Məkan:** {game['location']}\n"
        f"⏰ **Vaxt:** {game['time']}\n"
        f"📄 **Əlavə məlumat:** {game['extra_info']}\n"
    )

    await update.message.reply_text(game_info)

async def oyunubitir(update: Update, context: CallbackContext):
    """Starts the game finishing process by requesting match score."""
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in active_games:
        await query.answer("Hazırda aktiv oyun yoxdur!", show_alert=True)
        return

    context.user_data["finishing_game"] = user_id
    await query.message.reply_text("📊 Oyunun hesabını daxil edin:")
    return "SCORE"

async def list_participants(update: Update, context: CallbackContext):
    """Lists all participants of the current game."""
    user_id = update.effective_user.id

    if user_id not in active_games:
        await update.message.reply_text("❌ Oyun yoxdur, iştirakçı siyahısı boşdur.")
        return

    game = active_games[user_id]
    participants = game["participants"]

    if not participants:
        await update.message.reply_text("📜 Hazırda oyunda iştirak edən yoxdur.")
        return

    participant_list = "\n".join([f"• {p}" for p in participants])
    await update.message.reply_text(f"🎮 **İştirakçılar:**\n{participant_list}")


async def sesver(update: Update, context: CallbackContext):
    """Shows the list of participants for voting and allows users to vote."""
    user_id = update.effective_user.id

    if user_id not in active_games:
        await update.message.reply_text("❌ Hazırda aktiv oyun yoxdur, səsvermə mümkün deyil.")
        return

    game = active_games[user_id]
    participants = list(game["participants"])

    if not participants:
        await update.message.reply_text("📜 Oyunda iştirak edən yoxdur, səsvermə başlaya bilməz!")
        return

    # Səsvermə üçün inline keyboard yaradılır
    keyboard = [[InlineKeyboardButton(name, callback_data=f"vote_{name}")] for name in participants]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🗳 **Oyunun ən yaxşı oyunçusuna səs verin!**", reply_markup=reply_markup)

async def vote_handler(update: Update, context: CallbackContext):
    """Handles user votes and prevents multiple votes."""
    query = update.callback_query
    voter = query.from_user.id
    selected_player = query.data.split("_")[-1]

    if voter in vote_data:
        await query.answer("❌ Siz artıq səs vermisiniz!", show_alert=True)
        return

    vote_data[voter] = selected_player

    await query.answer("✅ Səsiniz qeydə alındı!")


async def announce_winner(context: CallbackContext):
    """Announces the best player after 1 hour of voting."""
    if not vote_data:
        return  # Heç kim səs verməyibsə, heç nə etmə

    vote_count = {}
    for player in vote_data.values():
        vote_count[player] = vote_count.get(player, 0) + 1

    # Ən çox səs alan oyunçunu tap
    best_player = max(vote_count, key=vote_count.get)

    # Qrupu ID kimi götürərək mesaj göndər
    chat_id = list(active_games.keys())[0]  # İlk oyunun olduğu qrup
    await context.bot.send_message(chat_id, f"🏆 **Oyunun ən yaxşısı {best_player} oldu!** 🎖")

    # Səsvermə məlumatlarını sıfırla
    vote_data.clear()





async def funksiyalar(update: Update, context: CallbackContext):
    """Shows all available commands in the bot."""
    commands_list = (
        "🤖 **Botun Mövcud Əmrləri:**\n\n"
        "🔹 `/start` - Botu başladır və qarşılama mesajı göstərir\n"
        "🔹 `/help` - Botun kömək mesajını göstərir\n"
        "🔹 `/info` - Bot haqqında məlumat verir\n"
        "🔹 `/contact` - Əlaqə məlumatlarını göstərir\n"
        "🔹 `/about` - Layihə haqqında məlumat verir\n"
        "🔹 `/oyunyarat` - Yeni oyun yaradır (yalnız adminlər üçün)\n"
        "🔹 `/oyun` - Hazırda aktiv oyunun məlumatlarını göstərir\n"
        "🔹 `/oyunubitir` - Oyunu bitir və nəticələri qeyd edir\n"
        "🔹 `/list` - Oyunda iştirak edənlərin siyahısını göstərir\n"
        "🔹 `+` - Oyuna qoşulmaq üçün istifadə olunur\n"
        "🔹 `-` - Oyundan çıxmaq üçün istifadə olunur\n"
        "🔹 `/sesver` - Oyunun ən yaxşı oyunçusuna səs vermək üçün istifadə olunur\n"
        "🔹 `/funksiyalar` - Botun bütün funksiyalarını göstərir\n\n"
        "📌 **Bundan əlavə, aşağıdakı butonlar da var:**\n"
        "✅ **OYUNA GƏLİRƏM** - Oyunda iştirak etməyi təsdiqləyir\n"
        "❌ **GƏLƏ BİLMİRƏM** - Oyundan imtina edir\n"
        "❌ **SİL** - Oyunu silir (yalnız yaradan şəxs istifadə edə bilər)\n"
        "🏁 **OYUNU BİTİR** - Oyunun nəticələrini qeydə alır\n"
    )

    await update.message.reply_text(commands_list)


async def handle_participation(update: Update, context: CallbackContext):
    """Handles users joining or leaving the game with + or - messages."""
    user_id = update.effective_user.id
    username = update.effective_user.first_name

    if user_id not in active_games:
        return  # Heç bir oyun yoxdursa, cavab vermə

    game = active_games[user_id]
    participants = game["participants"]

    if update.message.text == "+":
        if len(participants) >= 14:
            await update.message.reply_text("⚠️ Oyunda maksimum 14 nəfər iştirak edə bilər!")
            return
        
        participants.add(username)
        await list_participants(update, context)

    elif update.message.text == "-":
        participants.discard(username)
        await list_participants(update, context)

async def join_game(update: Update, context: CallbackContext):
    """Handles a user joining the game via button."""
    query = update.callback_query
    user_id = int(query.data.split("_")[-1])
    username = query.from_user.first_name

    if user_id not in active_games:
        await query.answer("❌ Bu oyun artıq mövcud deyil!", show_alert=True)
        return

    game = active_games[user_id]
    participants = game["participants"]

    if len(participants) >= 14:
        await query.answer("⚠️ Oyunda maksimum 14 nəfər iştirak edə bilər!", show_alert=True)
        return
    
    participants.add(username)
    await query.answer("✅ Oyuna əlavə olundunuz!")
    await list_participants(update, context)

async def leave_game(update: Update, context: CallbackContext):
    """Handles a user leaving the game via button."""
    query = update.callback_query
    user_id = int(query.data.split("_")[-1])
    username = query.from_user.first_name

    if user_id not in active_games:
        await query.answer("❌ Bu oyun artıq mövcud deyil!", show_alert=True)
        return

    game = active_games[user_id]
    game["participants"].discard(username)
    
    await query.answer("❌ Oyundan çıxarıldınız!")
    await list_participants(update, context)


async def set_score(update: Update, context: CallbackContext):
    """Stores the score and asks who won the game."""
    context.user_data["score"] = update.message.text
    await update.message.reply_text("🏆 Oyunu kim qazandı? (Komanda 1 / Komanda 2 / Heç-heçə)")
    return "WINNER"

async def set_winner(update: Update, context: CallbackContext):
    """Stores the winner and finishes the game."""
    user_id = context.user_data.get("finishing_game")

    if not user_id or user_id not in active_games:
        await update.message.reply_text("❌ Xəta baş verdi, oyun tapılmadı!")
        return ConversationHandler.END

    context.user_data["winner"] = update.message.text
    game = active_games.pop(user_id)  # Oyunu silirik, çünki bitdi

    game_summary = (
        f"🏁 **Oyun Bitdi!**\n\n"
        f"📍 **Məkan:** {game['location']}\n"
        f"⏰ **Vaxt:** {game['time']}\n"
        f"📄 **Əlavə məlumat:** {game['extra_info']}\n"
        f"📊 **Hesab:** {context.user_data['score']}\n"
        f"🏆 **Qalib:** {context.user_data['winner']}\n\n"
        f"🔔 **İndi isə /sesver komandasını yazaraq oyunun ən yaxşısını seçək!** 🎖️"
    )

    await update.message.reply_text(game_summary)
    await update.message.reply_text("🗳 **İndi /sesver yazaraq oyunun ən yaxşısını seçə bilərsiniz!** 🎖️")
    # 1 saat sonra ən yaxşı oyunçunu elan et
    context.job_queue.run_once(announce_winner, 3600)
    return ConversationHandler.END


def signal_handler(signum, frame):
    logger.info('Signal received, shutting down...')
    exit(0)

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("contact", contact))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("oyun", oyun, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))

    game_handler = ConversationHandler(
        entry_points=[CommandHandler("oyunyarat", oyun_yarat)],
        states={
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_location)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_time)],
            EXTRA_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_extra_info)]
        },
        fallbacks=[]
    )

    application.add_handler(game_handler)
    application.add_handler(CommandHandler("list", list_participants, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("funksiyalar", funksiyalar, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("sesver", sesver, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CallbackQueryHandler(vote_handler, pattern=r"vote_.*"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_participation))

    finish_game_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(oyunubitir, pattern=r"finish_game_\d+")],
    states={
        "SCORE": [MessageHandler(filters.TEXT & ~filters.COMMAND, set_score)],
        "WINNER": [MessageHandler(filters.TEXT & ~filters.COMMAND, set_winner)]
    },
    fallbacks=[]
)
    application.add_handler(finish_game_handler)
    application.add_handler(CallbackQueryHandler(join_game, pattern=r"join_game_\d+"))
    application.add_handler(CallbackQueryHandler(leave_game, pattern=r"leave_game_\d+"))
    application.add_handler(CallbackQueryHandler(delete_game, pattern=r"delete_game_\d+"))
    application.add_error_handler(error_handler)

    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
