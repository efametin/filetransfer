import logging
import sys
import os
import random
import asyncio
import signal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from threading import Timer

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

active_voting = None  # Hazırda aktiv səsverməni saxlayır
vote_timer = None  # Timer obyektini saxlayır

vote_data = {}

# Bitmiş oyun iştirakçılarını saxlayan dictionary
finished_games_participants = {}

# Bitmiş oyunların siyahısını saxlamaq üçün dictionary
finished_games = []

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
    """Oyun yaratma prosesini yalnız şəxsi mesajda icra etmək üçün yoxlayır."""

    if update.message.chat.type != "private":
        await update.message.reply_text(
            "🔒 Zəhmət olmasa botun şəxsi mesajına yazaraq oyunu yaradın."
        )
        return ConversationHandler.END

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
    """Oyun məlumatlarını tamamlayır və bütün qruplara elan edir."""

    user_id = update.message.from_user.id
    context.user_data["extra_info"] = update.message.text

    # Oyun məlumatlarını yadda saxla
    active_games[user_id] = {
        "location": context.user_data["location"],
        "time": context.user_data["time"],
        "extra_info": context.user_data["extra_info"],
        "creator": user_id,
        "participants": set()
    }

    game_info = (
        f"✅ Oyun yaradıldı!\n\n"
        f"📍 Məkan: {context.user_data['location']}\n"
        f"⏰ Vaxt: {context.user_data['time']}\n"
        f"📄 Əlavə məlumat: {context.user_data['extra_info']}\n"
    )

    # **İstifadəçiyə təsdiq göndər**
    await update.message.reply_text("✅ Oyun uğurla yaradıldı və bütün qruplara elan edildi!")

    # **Botun olduğu qruplara oyun elanını göndər**
    for chat_id in context.bot_data.get("groups", []):
        await context.bot.send_message(chat_id, game_info)

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
    """Oyunu yalnız şəxsi mesajda silməyə icazə verir."""

    if update.message.chat.type != "private":
        await update.message.reply_text(
            "🔒 Zəhmət olmasa botun şəxsi mesajına yazaraq oyunu silin."
        )
        return ConversationHandler.END

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


async def oyunubitir(update: Update, context: CallbackContext):
    """Oyunu yalnız şəxsi mesajda bitirməyə icazə verir."""

    if update.message.chat.type != "private":
        await update.message.reply_text(
            "🔒 Zəhmət olmasa botun şəxsi mesajına yazaraq oyunu bitirin."
        )
        return ConversationHandler.END

    await update.message.reply_text("🔑 Oyunu bitirmək üçün şifrəni daxil edin:")
    return "FINISH_PASSWORD"


async def check_finish_password(update: Update, context: CallbackContext):
    """Şifrəni yoxlayır və oyunu bitirmək prosesinə davam edir."""
    if update.message.text != GAME_CREATION_PASSWORD:  # Əgər şifrə yanlışdırsa
        await update.message.reply_text("❌ Şifrə yanlışdır! Oyun bitirilmədi.")
        return ConversationHandler.END

    await update.message.reply_text("📊 Oyunun hesabını daxil edin:")
    return "GAME_SCORE"

async def set_game_score(update: Update, context: CallbackContext):
    """Oyun hesabını təyin edir."""
    context.user_data["game_score"] = update.message.text
    await update.message.reply_text("🏆 Qalib komandanın adını daxil edin:")
    return "WINNER_TEAM"

async def set_winner_team(update: Update, context: CallbackContext):
    """Qalib komandanı təyin edir və oyunu yekunlaşdırır."""
    if not update.message.text.strip():
        await update.message.reply_text("❌ Düzgün qalib komandanın adını daxil edin:")
        return "WINNER_TEAM"

    context.user_data["winner_team"] = update.message.text
    chat_id = update.effective_chat.id  

    if chat_id in active_games:
        game = active_games.pop(chat_id)  
        participants = game["participants"]

    # **Yeni səsvermə başlat**
    if participants:
        global active_voting, vote_timer
        active_voting = {"chat_id": chat_id, "participants": list(participants), "votes": {}}

        def run_asyncio_task():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(announce_winner(chat_id, context.application))

        vote_timer = Timer(60, run_asyncio_task)  # 1 saat (3600 saniyə)
        vote_timer.start()

        # **Bitmiş oyun iştirakçılarını yadda saxla**
        finished_games_participants[chat_id] = list(participants)

        # **Bitmiş oyunu yadda saxla**
        finished_games.append({
            "chat_id": chat_id,
            "location": game["location"],
            "time": game["time"],
            "extra_info": game["extra_info"],
            "score": context.user_data["game_score"],
            "winner_team": context.user_data["winner_team"]
        })

        final_message = (
            f"🏁 Oyun başa çatdı!\n\n"
            f"📊 Hesab: {context.user_data['game_score']}\n"
            f"🏆 Qalib Komanda: {context.user_data['winner_team']}\n\n"
            f"🗳 Oyun bitib, artıq oyunun ən yaxşısını seçmək üçün `/sesver` əmrini yaza bilərsiniz!"
        )

        await update.message.reply_text(final_message)

    return ConversationHandler.END


async def save_group(update: Update, context: CallbackContext):
    """Botun olduğu qrupları yadda saxlayır."""
    chat = update.message.chat

    if chat.type in ["group", "supergroup"]:
        if "groups" not in context.bot_data:
            context.bot_data["groups"] = set()

        context.bot_data["groups"].add(chat.id)


async def bitmishoyunlar(update: Update, context: CallbackContext):
    """Bitmiş oyunların siyahısını göstərir."""
    if not finished_games:
        await update.message.reply_text("🔍 Hələ ki, heç bir bitmiş oyun yoxdur.")
        return

    result_text = "🏆 **Bitmiş Oyunlar:**\n\n"

    for idx, game in enumerate(finished_games, start=1):
        result_text += (
            f"🔹 Oyun {idx}\n"
            f"📍 Məkan: {game['location']}\n"
            f"⏰ Vaxt: {game['time']}\n"
            f"📄 Əlavə məlumat: {game['extra_info']}\n"
            f"📊 Hesab: {game['score']}\n"
            f"🏆 Qalib Komanda: {game['winner_team']}\n"
            f"-------------------------\n"
        )

    await update.message.reply_text(result_text)



async def sesver(update: Update, context: CallbackContext):
    """Aktiv səsverməni göstərir və istifadəçilərə səs verməyə icazə verir."""
    global active_voting

    if not active_voting:
        await update.message.reply_text("❌ Hazırda aktiv səsvermə yoxdur.")
        return

    chat_id = active_voting["chat_id"]
    if update.effective_chat.id != chat_id:
        await update.message.reply_text("❌ Bu səsvermə başqa bir oyun üçündür.")
        return

    keyboard = []
    for participant in active_voting["participants"]:
        vote_count = sum(1 for v in active_voting["votes"].values() if v == participant)
        button_text = f"{participant} - {vote_count} səs"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"vote_{participant}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🗳 Oyunun ən yaxşı oyunçusuna səs verin!", reply_markup=reply_markup)




async def vote_handler(update: Update, context: CallbackContext):
    """İstifadəçinin səsini qeydə alır və yenilənmiş nəticələri göstərir."""
    global active_voting

    query = update.callback_query
    voter = query.from_user.id
    selected_player = query.data.split("_")[-1]

    if not active_voting or voter in active_voting["votes"]:
        await query.answer("❌ Siz artıq səs vermisiniz!", show_alert=True)
        return

    active_voting["votes"][voter] = selected_player

    keyboard = []
    for participant in active_voting["participants"]:
        vote_count = sum(1 for v in active_voting["votes"].values() if v == participant)
        button_text = f"{participant} - {vote_count} səs"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"vote_{participant}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text("🗳 Oyunun ən yaxşı oyunçusuna səs verin!", reply_markup=reply_markup)
    await query.answer("✅ Səsiniz qeydə alındı!")



async def announce_winner(chat_id, application):
    """Səsvermə bitəndə qalibi elan edir və məlumatları sıfırlayır."""
    global active_voting, vote_timer

    if not active_voting or active_voting["chat_id"] != chat_id:
        return

    vote_count = {}
    for player in active_voting["votes"].values():
        vote_count[player] = vote_count.get(player, 0) + 1

    max_votes = max(vote_count.values(), default=0)
    top_players = [player for player, count in vote_count.items() if count == max_votes]

    winner = random.choice(top_players) if top_players else "Heç kim"

    # **Burada context yerinə application istifadə edirik!**
    await application.bot.send_message(chat_id, f"🏆 Oyunun ən yaxşı oyunçusu **{winner}** oldu! 🎖")

    # **Səsverməni sıfırlayırıq**
    active_voting = None
    vote_timer = None






async def funksiyalar(update: Update, context: CallbackContext):
    """Shows all available commands in the bot."""
    commands_list = (
        "🤖 Futbol botun mövcud əmrləri:\n\n"
        "🚀 `/start` - zzzzzBotu başladır\n"
        "🛠 `/funksiyalar` - Bütün əmrləri göstərir\n"
        "⚽ `/oyun` - Aktiv oyunun məlumatlarını göstərir\n"
        "👟 `/oyunagelirem` - Oyuna qoşulmaq üçün istifadə olunur\n"
        "💅 `/mengelmirem` - Futbola gəlmirəm, evdə dırnağıma lak çəkirəm!\n"
        "📜 `/list` - İştirakçı siyahısını göstərir\n"
        "🔥 `/sesver` - Oyunun ən yaxşı oyunçusuna səs ver (1 saat ərzində)!\n"
        "🆘 `/komek` - Kömək və əlaqə məlumatları\n"
        "🏆 `/bitmishoyunlar` - Bütün bitmiş oyunları göstər\n\n"
        "🔐 Şifrəli əmrlər:\n"
        "📢 `/oyunyarat` - Yeni oyun yaradır\n"
        "🏁 `/oyunubitir` - Oyunu bitir və nəticələri qeyd et\n"
        "🗑 `/oyunusil` - Oyunu sil\n"
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
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bitmishoyunlar", bitmishoyunlar))
    delete_game_handler = ConversationHandler(
    entry_points=[CommandHandler("oyunusil", oyunusil)],
    states={
        "DELETE_PASSWORD": [MessageHandler(filters.TEXT & ~filters.COMMAND, check_delete_password)]
    },
    fallbacks=[]
)
    application.add_handler(delete_game_handler)

    application.add_handler(CommandHandler("list", list_participants, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("funksiyalar", funksiyalar, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("komek", komek, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("sesver", sesver, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("oyunagelirem", oyunagelirem, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("mengelmirem", mengelmirem, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CallbackQueryHandler(vote_handler, pattern=r"vote_.*"))

    finish_game_handler = ConversationHandler(
    entry_points=[CommandHandler("oyunubitir", oyunubitir)],
    states={
        "FINISH_PASSWORD": [MessageHandler(filters.TEXT & ~filters.COMMAND, check_finish_password)],
        "GAME_SCORE": [MessageHandler(filters.TEXT & ~filters.COMMAND, set_game_score)],
        "WINNER_TEAM": [MessageHandler(filters.TEXT & ~filters.COMMAND, set_winner_team)]
    },
    fallbacks=[]
)

    # Yeni handleri əsas tətbiqə əlavə et
    application.add_handler(finish_game_handler)
    application.add_handler(MessageHandler(filters.ChatType.GROUPS, save_group))
   
    application.add_handler(CallbackQueryHandler(join_game, pattern=r"join_game_\d+"))
    application.add_handler(CallbackQueryHandler(leave_game, pattern=r"leave_game_\d+"))
    application.add_error_handler(error_handler)

    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
