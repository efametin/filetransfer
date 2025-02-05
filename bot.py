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

# BOTUN TOKENI
TOKEN = '7675127420:AAFbt7343zQWIBJ9eiwNxpo46yf6DHGf1Kg'


# State constants for ConversationHandler
PASSWORD, LOCATION, TIME, EXTRA_INFO = range(4)

# COMMANDLAR UCUN SIFRELER
START_PASSWORD = "1234"

# oyunyarat ve oyunubitir parolu
GAME_CREATION_PASSWORD = "1234"

# Dictionary to store ongoing game details
active_games = {}
vote_data = {}

async def start(update: Update, context: CallbackContext):
    """Həmişə sabit mesaj qaytaran sadə `/start` funksiyası."""
    await update.message.reply_text(
        "Futbol Bot başladıldı!\n\n"
        "✅ Artıq botun funksiyalarından istifadə edə bilərsiniz.\n"
        "📌 Bütün funksiyaları bilmək üçün `/funksiyalar` əmrini istifadə edin!"
    )


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
    chat_id = update.effective_chat.id

    # Store the game details
    active_games[chat_id] = {
        "location": context.user_data["location"],
        "time": context.user_data["time"],
        "extra_info": context.user_data["extra_info"],
        "creator": chat_id,
        "participants": set()
    }

    game_info = (
        f"✅ Oyun yaradıldı!\n\n"
        f"📍 Məkan: {context.user_data['location']}\n"
        f"⏰ Vaxt: {context.user_data['time']}\n"
        f"📄 Əlavə məlumat: {context.user_data['extra_info']}\n"
    )

    await update.message.reply_text(game_info)
    return ConversationHandler.END

async def delete_game(update: Update, context: CallbackContext):
    """Deletes the created game if the user is the creator."""
    query = update.callback_query
    chat_id = query.from_chat.id

    if chat_id in active_games:
        del active_games[chat_id]
        await query.message.edit_text("🗑️ Oyun uğurla silindi!")
    else:
        await query.answer("Bu oyunu silməyə icazəniz yoxdur!", show_alert=True)

async def oyun(update: Update, context: CallbackContext):
    """Shows the details of the currently active game."""
    chat_id = update.effective_chat.id

    if chat_id not in active_games:
        await update.message.reply_text("❌ Hazırda yaradılmış oyun yoxdur.")
        return

    game = active_games[chat_id]
    game_info = (
        f"🎮 Növbəti Oyunumuz:\n\n"
        f"📍 Məkan: {game['location']}\n"
        f"⏰ Vaxt: {game['time']}\n"
        f"📄 Əlavə məlumat: {game['extra_info']}\n"
    )

    await update.message.reply_text(game_info)


async def komek(update: Update, context: CallbackContext):
    """Provides help information when /komek is used."""
    help_text = (
        "📌 Kömək Məlumatı:\n\n"
        "✅ Əgər oyunla bağlı sualınız varsa, Ravanin nömrəsinə WhatsApp-da yaza və ya zəng edə bilərsiniz.\n"
        "---\n"
        "⚠️ Yox əgər bu botda problem görmüsüzsə, söymüyün 😄 WhatsApp-da yazın, problemi həll edim! +99455555555343 😉"
    )

    await update.message.reply_text(help_text)

async def oyunubitir(update: Update, context: CallbackContext):
    """Oyunu bitirmək üçün parolu yoxlayır."""
    chat_id = update.effective_chat.id  # Düzgün istifadə
    if chat_id not in active_games:
        await update.message.reply_text("❌ Hal-hazırda bitiriləcək oyun yoxdur.")
        return ConversationHandler.END

    context.user_data["finishing_game"] = chat_id
    await update.message.reply_text("🔑 Oyunu bitirmək üçün parolu daxil edin:")
    return "FINISH_PASSWORD"  # Şifrə yoxlama mərhələsinə keçir

async def check_finish_password(update: Update, context: CallbackContext):
    """Verifies the password and proceeds to game finishing process."""
    if update.message.text.strip() != GAME_CREATION_PASSWORD:  # Şifrəni boşluqlardan təmizləyək
        await update.message.reply_text("❌ Parol yanlışdır! Oyun bitirilmədi.")
        return ConversationHandler.END

    chat_id = context.user_data.get("finishing_game")
    if not chat_id or chat_id not in active_games:
        await update.message.reply_text("❌ Xəta baş verdi, oyun tapılmadı!")
        return ConversationHandler.END

    await update.message.reply_text("📊 Oyunun hesabını daxil edin:")
    return "SCORE"

async def list_participants(update: Update, context: CallbackContext):
    """Lists all participants of the current game."""
    chat_id = update.effective_chat.id  # Qrupun ID-sini al

    if chat_id not in active_games:  # Əgər aktiv oyun yoxdursa
        await update.message.reply_text("❌ Oyun yoxdur, iştirakçı siyahısı boşdur.")
        return

    game = active_games[chat_id]  # Oyun məlumatlarını əldə et
    participants = game["participants"]  # İştirakçıların siyahısını al

    if not participants:  # Əgər iştirakçı yoxdursa
        await update.message.reply_text("📜 Hazırda oyunda iştirak edən yoxdur.")
        return

    # **OYUN MƏLUMATLARI**
    game_info = (
        f"📍 Məkan: {game['location']}\n"
        f"⏰ Vaxt: {game['time']}\n"
    )

    # **İŞTİRAKÇILAR**
    participant_list = "\n".join([f"• {p}" for p in participants])  # Siyahını düzəlt

    # **Nəticəni ekrana çıxart**
    await update.message.reply_text(f"🎮 Oyun Məlumatları:\n\n{game_info}\n🎮 Oyuna gələnlər:\n{participant_list}")


async def oyunusil(update: Update, context: CallbackContext):
    """Aktiv oyunu silmək üçün şifrə tələb edir."""
    chat_id = update.effective_chat.id  # Qrupun ID-sini al

    if chat_id not in active_games:  # Əgər aktiv oyun yoxdursa
        await update.message.reply_text("❌ Hal-hazırda silinə biləcək aktiv oyun yoxdur.")
        return

    await update.message.reply_text("🔑 Oyunu silmək üçün şifrəni daxil edin:")
    return "DELETE_PASSWORD"

async def check_delete_password(update: Update, context: CallbackContext):
    """Şifrəni yoxlayır və oyunu silir."""
    if update.message.text != GAME_CREATION_PASSWORD:  # Əgər şifrə yanlışdırsa
        await update.message.reply_text("❌ Şifrə yanlışdır! Oyun silinmədi.")
        return ConversationHandler.END

    chat_id = update.effective_chat.id  # Qrupun ID-sini al

    if chat_id in active_games:  # Əgər oyun mövcuddursa, onu sil
        del active_games[chat_id]
        await update.message.reply_text("🗑️ Oyun uğurla silindi!")
    else:
        await update.message.reply_text("❌ Artıq silinə biləcək aktiv oyun yoxdur.")

    return ConversationHandler.END


async def sesver(update: Update, context: CallbackContext):
    """Shows the list of participants for voting and allows users to vote."""
    chat_id = update.effective_chat.id

    if chat_id not in active_games:
        await update.message.reply_text("❌ Hazırda aktiv oyun yoxdur, səsvermə mümkün deyil.")
        return

    game = active_games[chat_id]
    participants = list(game["participants"])

    if not participants:
        await update.message.reply_text("📜 Oyunda iştirak edən yoxdur, səsvermə başlaya bilməz!")
        return

    # Səsvermə üçün inline keyboard yaradılır
    keyboard = [[InlineKeyboardButton(name, callback_data=f"vote_{name}")] for name in participants]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🗳 Oyunun ən yaxşı oyunçusuna səs verin!", reply_markup=reply_markup)

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
    await context.bot.send_message(chat_id, f"🏆 Oyunun ən yaxşısı {best_player} oldu! 🎖")

    # Səsvermə məlumatlarını sıfırla
    vote_data.clear()


async def funksiyalar(update: Update, context: CallbackContext):
    """Shows all available commands in the bot."""
    commands_list = (
        "🤖 Futbol botun mövcud əmrləri:\n\n"
        "🤖 Admin əmrləri:\n\n"
        "🔹 `/start` - Botu başladır \n"
        "🔹 `/oyunyarat` - Yeni oyun yaradır \n"
        "🔹 `/oyunubitir` - Oyunu bitirir və nəticələri qeyd edir \n"
        "🔹 `/oyunusil` - Oyunu silir \n"
        "🔹 `/funksiyalar` - Botun bütün funksiyalarını göstərir\n\n"
        "🔹 `/oyun` - Hazırda aktiv oyunun məlumatlarını göstərir\n"

        "🔹 `/list` - Oyunda iştirak edənlərin siyahısını göstərir\n"
        "🔹 `/oyunagelirem` - Oyuna qoşulmaq üçün istifadə olunur\n"
        "🔹 `/mengelmirem` - Oyundan çıxmaq üçün istifadə olunur\n"
        "🔹 `/sesver` - Oyunun ən yaxşı oyunçusuna səs vermək üçün istifadə olunur\n"
        "🔹 `/komek` - Oyunun ən yaxşı oyunçusuna səs vermək üçün istifadə olunur\n"
        "📌 Bundan əlavə, aşağıdakı butonlar da var:\n"
        "❌ SİL - Oyunu silir (yalnız şifrəni bilən silə bilir)\n"
        "🏁 OYUNU BİTİR - Oyunu bitirir (yalnız şifrəni bilən silə bilir)\n"
    )

    await update.message.reply_text(commands_list)

async def join_game(update: Update, context: CallbackContext):
    """Handles a user joining the game via button."""
    query = update.callback_query
    chat_id = int(query.data.split("_")[-1])
    username = query.from_user.first_name

    if chat_id not in active_games:
        await query.answer("❌ Bu oyun artıq mövcud deyil!", show_alert=True)
        return

    game = active_games[chat_id]
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
    chat_id = int(query.data.split("_")[-1])
    username = query.from_user.first_name

    if chat_id not in active_games:
        await query.answer("❌ Bu oyun artıq mövcud deyil!", show_alert=True)
        return

    game = active_games[chat_id]
    game["participants"].discard(username)
    
    await query.answer("❌ Oyundan çıxarıldınız!")
    await list_participants(update, context)


async def oyunagelirem(update: Update, context: CallbackContext):
    """Handles a user joining the game via /oyunagelirem command."""
    chat_id = update.effective_chat.id  # Qrupun ID-sini al
    user_id = update.effective_user.id  # İstifadəçinin ID-sini al
    username = update.effective_user.first_name  # İstifadəçinin adını al

    if chat_id not in active_games:  # Qrup üçün aktiv oyun varmı?
        await update.message.reply_text("❌ Hazırda aktiv oyun yoxdur.")
        return

    game = active_games[chat_id]  # Qrup üçün oyun məlumatlarını götür
    participants = game["participants"]

    if len(participants) >= 14:  # Limit yoxlanışı
        await update.message.reply_text("⚠️ Oyunda maksimum 14 nəfər iştirak edə bilər!")
        return
    
    participants.add(username)  # İstifadəçini əlavə et
    await update.message.reply_text(f"✅ {username} oyuna qoşuldu!")  # Təsdiq mesajı
    await list_participants(update, context)  # Yenilənmiş siyahını göstər


async def mengelmirem(update: Update, context: CallbackContext):
    """Handles a user leaving the game via /mengelmirem command."""
    chat_id = update.effective_chat.id  # Qrupun ID-sini al
    user_id = update.effective_user.id  # İstifadəçinin ID-sini al
    username = update.effective_user.first_name  # İstifadəçinin adını al

    if chat_id not in active_games:  # Qrup üçün aktiv oyun varmı?
        await update.message.reply_text("❌ Hazırda aktiv oyun yoxdur.")
        return

    game = active_games[chat_id]  # Qrup üçün oyun məlumatlarını götür
    game["participants"].discard(username)  # İstifadəçini iştirakçılardan çıxar

    await update.message.reply_text(f"❌ {username} oyundan çıxdı!")  # Təsdiq mesajı
    await list_participants(update, context)  # Yenilənmiş siyahını göstər

async def set_score(update: Update, context: CallbackContext):
    """Stores the score and asks who won the game."""
    context.user_data["score"] = update.message.text
    await update.message.reply_text("🏆 Oyunu kim qazandı? (Komanda 1 / Komanda 2 / Heç-heçə)")
    return "WINNER"

async def set_winner(update: Update, context: CallbackContext):
    """Stores the winner and finishes the game."""
    chat_id = context.user_data.get("finishing_game")

    if not chat_id or chat_id not in active_games:
        await update.message.reply_text("❌ Xəta baş verdi, oyun tapılmadı!")
        return ConversationHandler.END

    context.user_data["winner"] = update.message.text
    game = active_games.pop(chat_id)  # Oyunu silirik, çünki bitdi

    game_summary = (
        f"🏁 Oyun Bitdi!\n\n"
        f"📍 Məkan: {game['location']}\n"
        f"⏰ Vaxt: {game['time']}\n"
        f"📄 Əlavə məlumat: {game['extra_info']}\n"
        f"📊 Hesab: {context.user_data['score']}\n"
        f"🏆 Qalib: {context.user_data['winner']}\n\n"
        f"🔔 Indi isə /sesver komandasını yazaraq oyunun ən yaxşısını seçək! 🎖️"
    )

    await update.message.reply_text(game_summary)
    await update.message.reply_text("🗳 **İndi /sesver yazaraq oyunun ən yaxşısını seçə bilərsiniz!** 🎖️")
    return ConversationHandler.END

def signal_handler(signum, frame):
    logger.info('Signal received, shutting down...')
    exit(0)

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
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
    application.add_handler(CommandHandler("oyunubitir", oyunubitir))
    application.add_handler(CommandHandler("start", start))
    delete_game_handler = ConversationHandler(
    entry_points=[CommandHandler("oyunusil", oyunusil)],
    states={
        "DELETE_PASSWORD": [MessageHandler(filters.TEXT & ~filters.COMMAND, check_delete_password)]
    },
    fallbacks=[]
)
    application.add_handler(delete_game_handler)

    finish_game_handler = ConversationHandler(
    entry_points=[CommandHandler("oyunubitir", oyunubitir)],
    states={
        "FINISH_PASSWORD": [MessageHandler(filters.TEXT & ~filters.COMMAND, check_finish_password)],
        "SCORE": [MessageHandler(filters.TEXT & ~filters.COMMAND, set_score)],
        "WINNER": [MessageHandler(filters.TEXT & ~filters.COMMAND, set_winner)]
    },
    fallbacks=[]
)
    application.add_handler(finish_game_handler)

    
    application.add_handler(CommandHandler("list", list_participants, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("funksiyalar", funksiyalar, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("komek", komek, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("sesver", sesver, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("oyunagelirem", oyunagelirem, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("mengelmirem", mengelmirem, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CallbackQueryHandler(vote_handler, pattern=r"vote_.*"))

    application.add_handler(CallbackQueryHandler(join_game, pattern=r"join_game_\d+"))
    application.add_handler(CallbackQueryHandler(leave_game, pattern=r"leave_game_\d+"))
    application.add_error_handler(error_handler)

    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
