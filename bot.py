import logging
import sys
import os
import random
import asyncio
import signal
import time
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

# **Qrupun ID-sini təyin edirik**
GROUP_CHAT_ID = -1002369357283  # 🔹 **Bura öz qrupunun ID-sini yaz!**
GROUP_ADMIN_ID = 1134292718  # Matin A. hesabının ID-sidir..!

# State constants for ConversationHandler
PASSWORD, LOCATION, TIME, EXTRA_INFO = range(4)

# oyunyarat ve oyunubitir parolu
GAME_CREATION_PASSWORD = "1234"

# Dictionary to store ongoing game details
active_games = {}
user_game_request_times = {}
user_start_times = {}
user_list_times = {}
user_komek_times = {}

active_voting = None  # Hazırda aktiv səsverməni saxlayır
vote_timer = None  # Timer obyektini saxlayır

vote_data = {}

# Bitmiş oyun iştirakçılarını saxlayan dictionary
finished_games_participants = {}

# Bitmiş oyunların siyahısını saxlamaq üçün dictionary
finished_games = []

async def start(update: Update, context: CallbackContext):
    """İstifadəçi /start yazdıqda salam mesajı göndərir və 24 saat məhdudiyyəti tətbiq edilir."""
    user_id = update.effective_user.id  # İstifadəçinin Telegram ID-si
    chat_id = update.effective_chat.id  # Mesajın gəldiyi chatın ID-si
    current_time = time.time()  # İndiki timestamp (Unix vaxtı)

    # 24 saat məhdudiyyətini yoxlayırıq (86,400 saniyə)
    if user_id in user_start_times and (current_time - user_start_times[user_id]) < 60:
        return  # Əgər 24 saat keçməyibsə, heç nə etmirik və bot cavab vermir

    user_start_times[user_id] = current_time  # İstifadəçinin son `/start` çağırma vaxtını yeniləyirik
    username = update.effective_user.first_name  # İstifadəçinin adı
    bot_name = context.bot.first_name  # Botun adı

    message = (
        f"🎉 {username}, aramıza xoş gəldin! 😊\n\n"
        "⚽ Bu futbol qrupunda oyunun təşkil edilməsi prosesi *bot* vasitəsilə tənzimlənir!\n\n"
        "📌 Botun xüsusiyyətlərini öyrənmək üçün `/funksiyalar` əmrini yaza bilərsən! 🔥"
    )

    # **Mesajı adi mesaj kimi göndəririk, reply olaraq yox!**
    await context.bot.send_message(chat_id=chat_id, text=message)



async def get_chat_id(update: Update, context: CallbackContext):
    """Bu funksiya yalnız botla şəxsi mesajda işləyir və chat ID-ni qaytarır."""
    if update.message.chat.type != "private":
        return  # Qrupda çağırılıbsa, heç bir reaksiya vermirik

    chat_id = update.message.chat.id
    await update.message.reply_text(f"Bu chatın ID-si: `{chat_id}`", parse_mode="Markdown")


async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Sorry, something went wrong. Please try again later."
        )

async def oyun_yarat(update: Update, context: CallbackContext):
    """Starts the game creation process in private chat only."""
    
    # **Əgər istifadəçi bu əmri qrupda yazırsa, bot heç bir reaksiya verməsin.**
    if update.message.chat.type != "private":
        return  # Bot heç nə yazmır, sadəcə susur

    await update.message.reply_text("🔑 Oyunu yaratmaq üçün şifrə daxil edin:")
    return PASSWORD  # **Növbəti mərhələ: Şifrə yoxlanışı**


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
    """Sets additional game details and announces the game in the group."""
    context.user_data["extra_info"] = update.message.text
    chat_id = update.effective_chat.id  # Şəxsi mesaj chat ID

    # Oyunu yaradan istifadəçinin ID-sini alırıq
    creator_id = update.effective_user.id  

    # Oyun detalları
    game_info = (
        f"⚽ Matç Yaradıldı!\n\n"
        f"📍 Məkan: {context.user_data['location']}\n"
        f"⏰ Vaxt: {context.user_data['time']}\n"
        f"📄 Əlavə Məlumat: {context.user_data['extra_info']}\n"
        f"👤 Təşkilatçı: [{update.effective_user.first_name}](tg://user?id={creator_id})\n\n"
        f"⚠️ Oyunda iştirak etmək üçün `/gelirem` əmrini, "
        f"iştirak etməkdən imtina üçün `/gelmirem` əmrini yazın qrupa.\n"
        f"Təşkil edilmiş futbol matçında iştirak edəcək şəxslərin listinə baxmaq üçün qrupa `/list` yazaraq göndərin.\n"
        f"Digər bütün funksiyalar üçün isə, `/funksiyalar` yazaraq göndərib baxa bilərsiniz..\n"
    )

    # Oyunu yadda saxlayaq
    active_games[GROUP_CHAT_ID] = {
        "location": context.user_data["location"],
        "time": context.user_data["time"],
        "extra_info": context.user_data["extra_info"],
        "creator": creator_id,
        "participants": set()
    }

    # Oyunu yaradan istifadəçiyə təsdiq mesajı
    await update.message.reply_text("✅ Oyun yaradıldı və qrupa göndərildi!")

    # ✅ **Oyun məlumatlarını qrupa göndəririk**
    await context.bot.send_message(GROUP_CHAT_ID, game_info, parse_mode="Markdown")

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

# Hər bir istifadəçinin son /oyun çağırma vaxtını saxlayan dictionary
user_game_request_times = {}

async def komanda_qur(update: Update, context: CallbackContext):
    """İştirakçılar 12 nəfərə çatanda, avtomatik olaraq onları 2 komandaya bölür və qrupa göndərir."""
    chat_id = update.effective_chat.id  # Qrup ID-si

    # Əgər qrupda oyun yoxdursa
    if chat_id not in active_games:
        return

    game = active_games[chat_id]
    participants = list(game["participants"])

    # Əgər iştirakçı sayı 12 deyilsə, funksiya işləmir
    if len(participants) != 12:
        return

    # İştirakçıları random şəkildə qarışdırırıq və iki komandaya bölürük
    random.shuffle(participants)
    team1 = participants[:6]
    team2 = participants[6:]

    # Mesaj formatı
    message = (
        "⚽ *Komandalar Təyin Olundu!* ⚽\n\n"
        "🏅 *Komanda 1:*\n" +
        "\n".join([f"🔹 {player}" for player in team1]) +
        "\n\n⚔️ VS\n\n" +
        "🏆 *Komanda 2:*\n" +
        "\n".join([f"🔸 {player}" for player in team2]) +
        "\n\n🔥 Uğurlar hər kəsə!"
    )

    await context.bot.send_message(chat_id, message, parse_mode="Markdown")
 
async def oyun(update: Update, context: CallbackContext):
    """Hazırda aktiv oyunun məlumatlarını göstərir. 
    - Bot qrupda mesajı reply etmədən göndərir.
    - İstifadəçilər 10 dəqiqədən bir çağır bilər.
    - Botun öz çağırışları məhdudlaşdırılmır.
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id  # İstifadəçinin ID-si
    current_time = time.time()  # İndiki timestamp (Unix vaxtı)

    # Əgər bot öz-özünə bu funksiyanı çağırıbsa, məhdudiyyət tətbiq etmirik
    if not update.effective_user.is_bot:
        # Əgər istifadəçi son 10 dəqiqə ərzində bu əmri çağırıbsa, bot cavab vermir
        if user_id in user_game_request_times and (current_time - user_game_request_times[user_id]) < 60:
            return  # Heç bir reaksiya vermirik

        # Yeni çağırma vaxtını yadda saxlayırıq
        user_game_request_times[user_id] = current_time  

    if chat_id not in active_games:
        return  # Qrupda oyun yoxdursa, heç nə göndərmirik

    game = active_games[chat_id]
    game_info = (
        f"⚽ Gələcək Futbol Oyunumuz ⚽\n"
        f"📍 Oyunun yeri: {game['location']}\n"
        f"⏰ Başlama vaxtı: {game['time']}\n"
        f"📄 Əlavə məlumat: {game['extra_info']}\n\n"
        f"Bu oyunda səni görmək xoş olar. Oyuna gəlmək istəsən `/gelirem` yazaraq matça qoşula bilərsən! ⚽"
    )

    # **Mesajı adi mesaj kimi göndəririk, reply olaraq yox!**
    await context.bot.send_message(chat_id=chat_id, text=game_info)



async def komek(update: Update, context: CallbackContext):
    """İstifadəçi `/komek` yazanda 1 saatlıq məhdudiyyət tətbiq edən funksiya.
       Əgər 1 saat keçməyibsə, bot heç bir reaksiya vermir.
    """
    
    user_id = update.effective_user.id  # İstifadəçinin Telegram ID-si
    current_time = time.time()  # İndiki vaxt (timestamp)
    
    # **Əgər istifadəçi son dəfə bu əmri yazıbsa və 1 saat keçməyibsə, heç bir reaksiya vermirik.**
    if user_id in user_komek_times and (current_time - user_komek_times[user_id]) < 60:
        return  # Sadəcə bot susur, heç nə cavab vermir.

    # **Əgər 1 saat keçibsə və ya ilk dəfə yazılırsa, əmri icra edirik**
    user_komek_times[user_id] = current_time  # Vaxtı yadda saxlayırıq

    # **İstifadəçinin adını və username-i alırıq**
    user = update.effective_user
    user_mention = f"@{user.username}" if user.username else user.first_name  # Username varsa, onu götür, yoxdursa adını
    
    # **WhatsApp və Zəng üçün linklər**
    whatsapp_link = "https://wa.me/994555706040"
    call_link = "tel:+994555706040"

    # **Mesaj məzmunu**
    help_text = (
        f"🧞‍♂️ Salam {user_mention}, deyəsən köməyə ehtiyacın var! 😊\n\n"
        "Oynayacağımız mini futbol matçıyla bağlı, ya da botda qarşılaşdığın hər hansı problemlə bağlı sualın varsa, "
        f"[whatsapp-dan]({whatsapp_link}) yazaraq və ya [zəng]({call_link}) edərək əlaqə saxlaya bilərsən. 📞"
    )

    # **Mesajı reply etmədən, normal mesaj kimi göndəririk**
    await context.bot.send_message(update.effective_chat.id, help_text, parse_mode="Markdown")



async def list_participants(update: Update, context: CallbackContext, called_by_bot=False):
    """Lists all participants of the current game. If called_by_bot=True, it bypasses the cooldown."""
    
    user_id = update.effective_user.id  # İstifadəçinin Telegram ID-si
    chat_id = update.effective_chat.id  # Qrupun ID-sini al
    current_time = time.time()  # İndiki vaxt (timestamp)
    
    # **Əgər funksiya istifadəçi tərəfindən çağırılırsa və 5 dəqiqə keçməyibsə**
    if not called_by_bot and user_id in user_list_times and (current_time - user_list_times[user_id]) < 30:  # 300 saniyə = 5 dəqiqə
        await update.effective_message.reply_text(
            "⚠️ Az öncə siyahını paylaşmışam, zəhmət olmasa 5 dəqiqə sonra yenidən yoxlayın!"
        )
        return  # Əmr icra olunmur
    
    # **Əgər 5 dəqiqə keçibsə və ya bot tərəfindən çağırılırsa**
    user_list_times[user_id] = current_time  # Vaxtı yadda saxlayırıq (yalnız istifadəçilər üçün)

    if chat_id not in active_games:  # Əgər aktiv oyun yoxdursa
        await update.message.chat.send_message("❌ Oyun yoxdur, iştirakçı siyahısı boşdur.")
        return

    game = active_games[chat_id]  # Oyun məlumatlarını əldə et
    participants = list(game["participants"])  # İştirakçıların siyahısını al

    if not participants:  # Əgər iştirakçı yoxdursa
        await update.message.chat.send_message("📜 Hazırda oyunda iştirak edən yoxdur.")
        return

    # **OYUN MƏLUMATLARI**
    game_info = (
        f"📍 Oyunun ünvanı: {game['location']}\n"
        f"⏰ Başlama vaxtı: {game['time']}\n"
    )

    # **İŞTİRAKÇILAR - Sıra ilə yazılır (1., 2., 3.)**
    participant_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(participants)])

    # **Nəticəni normal mesaj kimi göndəririk (reply olmadan)**
    await update.message.chat.send_message(f"⚽ Matç məlumatları:\n{game_info}\n Oyuna gələnlər:\n{participant_list}", parse_mode="Markdown")


async def oyunusil(update: Update, context: CallbackContext):
    """Aktiv oyunu silmək üçün şifrə tələb edir. Yalnız şəxsi mesajda işləyir."""
    
    # **Əgər istifadəçi bu əmri qrupda yazırsa, bot susur (reaksiya vermir).**
    if update.message.chat.type != "private":
        return  # Bot heç nə yazmır

    chat_id = GROUP_CHAT_ID  # Oyunun olduğu qrupun ID-si

    if chat_id not in active_games:  # Əgər aktiv oyun yoxdursa
        await update.message.reply_text("❌ Hazırda silinə biləcək aktiv oyun yoxdur.")
        return

    await update.message.reply_text("🔑 Oyunu silmək üçün şifrəni daxil edin:")
    return "DELETE_PASSWORD"  # **Növbəti mərhələ: Şifrə yoxlanışı**


async def check_delete_password(update: Update, context: CallbackContext):
    """Şifrəni yoxlayır və oyunu silir."""
    
    chat_id = GROUP_CHAT_ID  # Oyunun olduğu qrupun ID-si

    # **Əgər şifrə səhvdirsə**
    if update.message.text != GAME_CREATION_PASSWORD:
        await update.message.reply_text("❌ Şifrə yanlışdır! Oyun silinmədi.")
        return ConversationHandler.END  # Prosesi bitiririk

    # **Əgər şifrə düzdürsə və oyun varsa, onu silirik**
    if chat_id in active_games:
        del active_games[chat_id]  # Oyunu silirik

        # **Şəxsi mesajda təsdiq mesajı**
        await update.message.reply_text("✅ Oyun uğurla silindi!")

        # **Qrupa elan göndəririk**
        await context.bot.send_message(chat_id, "🗑️ Son yaradılmış oyun silindi! ❌")

    else:
        await update.message.reply_text("❌ Artıq silinə biləcək aktiv oyun yoxdur.")

    return ConversationHandler.END  # Prosesi bitiririk


async def oyunubitir(update: Update, context: CallbackContext):
    """Oyun bitirmək əmri yalnız şəxsi mesajda işləyir və şifrə tələb edir."""
    
    # **Əgər istifadəçi bu əmri qrupda yazırsa, bot heç bir reaksiya verməsin.**
    if update.message.chat.type != "private":
        return  # Bot susur və heç bir mesaj yazmır

    chat_id = GROUP_CHAT_ID  # Oyunun keçirildiyi qrupun ID-si

    if chat_id not in active_games:  # Əgər aktiv oyun yoxdursa
        await update.message.reply_text("❌ Hal-hazırda bitiriləcək aktiv oyun yoxdur.")
        return

    await update.message.reply_text("🔑 Oyunu bitirmək üçün şifrəni daxil edin:")
    return "FINISH_PASSWORD"  # **Növbəti mərhələ: Şifrə yoxlanışı**


async def check_finish_password(update: Update, context: CallbackContext):
    """Şifrəni yoxlayır və oyunu bitirmək prosesinə davam edir."""
    
    if update.message.text != GAME_CREATION_PASSWORD:  # Əgər şifrə yanlışdırsa
        await update.message.reply_text("❌ Şifrə yanlışdır! Oyun bitirilmədi.")
        return ConversationHandler.END  # Prosesi bitiririk

    await update.message.reply_text("📊 Oyunun hesabını daxil edin:")
    return "GAME_SCORE"  # **Növbəti mərhələ: Oyun hesabının daxil edilməsi**


async def set_game_score(update: Update, context: CallbackContext):
    """Oyun hesabını yadda saxlayır."""
    
    context.user_data["game_score"] = update.message.text
    await update.message.reply_text("🏆 Qalib komandanın adını daxil edin:")
    return "WINNER_TEAM"  # **Növbəti mərhələ: Qalib komandanın adı**


async def set_winner_team(update: Update, context: CallbackContext):
    """Qalib komandanı yadda saxlayır və oyunu yekunlaşdırır."""
    
    if not update.message.text.strip():
        await update.message.reply_text("❌ Düzgün qalib komandanın adını daxil edin:")
        return "WINNER_TEAM"

    context.user_data["winner_team"] = update.message.text
    chat_id = GROUP_CHAT_ID  # Oyunun keçirildiyi qrupun ID-si

    if chat_id in active_games:
        game = active_games.pop(chat_id)  # Oyunu aktiv siyahıdan çıxarırıq
        participants = game["participants"]

    # **Əgər oyun iştirakçıları varsa, səsvermə üçün məlumatları hazırlayırıq**
    if participants:
        global active_voting, vote_timer
        active_voting = {"chat_id": chat_id, "participants": list(participants), "votes": {}}

        def run_asyncio_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(announce_winner(chat_id, context.application))

        vote_timer = Timer(3600, run_asyncio_task)  # 1 saat (3600 saniyə)
        vote_timer.start()

        # **Bitmiş oyunun məlumatlarını yadda saxlayırıq**
        finished_games.append({
            "chat_id": chat_id,
            "location": game["location"],
            "time": game["time"],
            "extra_info": game["extra_info"],
            "score": context.user_data["game_score"],
            "winner_team": context.user_data["winner_team"]
        })

        # **Qrupa mesaj göndəririk ki, oyun başa çatdı**
        final_message = (
            "🏁 *Oyun başa çatdı!* 🎉\n\n"
            f"📊 *Hesab:* {context.user_data['game_score']}\n"
            f"🏆 *Qalib Komanda:* {context.user_data['winner_team']}\n\n"
            "🗳 *Oyunun ən yaxşı oyunçusunu seçmək üçün `/sesver` əmrini istifadə edin!*"
        )

        await context.bot.send_message(chat_id, final_message, parse_mode="Markdown")

    return ConversationHandler.END  # Prosesi bitiririk





async def bitmishoyunlar(update: Update, context: CallbackContext):
    """Bitmiş oyunların siyahısını göstərir."""
    if not finished_games:
        await update.message.reply_text("🔍 Hələ ki, heç bir bitmiş oyun yoxdur.")
        return

    result_text = "🏆 Bitmiş Oyunlar:\n\n"

    for idx, game in enumerate(finished_games, start=1):
        result_text += (
            f"🔹 Oyun {idx}\n"
            f"📍 Məkan: {game['location']}\n"
            f"⏰ Vaxt: {game['time']}\n"
            f"📄 Əlavə məlumat: {game['extra_info']}\n"
            f"📊 Hesab: {game['score']}\n"
            f"🏆 Qalib Komanda: {game['winner_team']}\n"
            f"---\n"
        )

    await update.message.reply_text(result_text)


async def sesver(update: Update, context: CallbackContext):
    """Aktiv səsverməni göstərir və istifadəçilərə səs verməyə icazə verir."""
    global active_voting

    if not active_voting:
        return  # Əgər səsvermə yoxdursa, heç bir cavab vermirik

    chat_id = active_voting["chat_id"]
    if update.effective_chat.id != chat_id:
        return  # Əgər bu səsvermə başqa qrup üçündürsə, cavab vermirik

    voter_name = update.effective_user.first_name  # İstifadəçinin adı
    voter_id = update.effective_user.id  # İstifadəçinin ID-si

    keyboard = []
    for participant in active_voting["participants"]:
        if participant == voter_name:  
            continue  # **İstifadəçi öz adını görməsin, özünə səs verə bilməsin!**

        vote_count = sum(1 for v in active_voting["votes"].values() if v == participant)
        button_text = f"{participant} - {vote_count} səs"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"vote_{participant}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id, "🗳 Oyunun ən yaxşı oyunçusuna səs verin! Nəzərə al ki, səsi geri çəkmək və ya silmək olmur ! SƏS VERƏNDƏ DİQQƏTLİ OL!", reply_markup=reply_markup)


async def vote_handler(update: Update, context: CallbackContext):
    """İstifadəçinin səsini qeydə alır və yenilənmiş nəticələri göstərir."""
    global active_voting

    query = update.callback_query
    voter_id = query.from_user.id
    voter_name = query.from_user.first_name
    selected_player = query.data.split("_")[-1]

    # **İstifadəçi özünə səs verə bilməz**
    if voter_name == selected_player:
        await query.answer("❌ Özünə səs verə bilməzsən!", show_alert=True)
        return

    if not active_voting or voter_id in active_voting["votes"]:
        await query.answer("❌ Siz artıq səs vermisiniz!", show_alert=True)
        return

    active_voting["votes"][voter_id] = selected_player

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

    if not vote_count:
        await application.bot.send_message(chat_id, "❌ Heç kim səs almadı, qalib yoxdur!")
        return

    max_votes = max(vote_count.values(), default=0)
    top_players = [player for player, count in vote_count.items() if count == max_votes]

    winner = random.choice(top_players) if top_players else "Heç kim"

    # 🔥 **Yeni qalib mesajı**
    winner_message = (
        "🏆🔥 *SON OYUNUN ƏN YAXŞI OYUNÇUSU!* 🔥🏆\n\n"
        f"🎖 *Man of the Match:* **{winner}** 🎖\n\n"
        "👏 Təbriklər! Oyunda əla performans göstərdin! 👏\n\n"
        "⚽ Səs verən hər kəsə təşəkkürlər! 🙌\n"
        "🚀 Gələcək oyunlarda uğurlar!"
    )

    # **Mesajı reply etmədən göndəririk**
    await application.bot.send_message(chat_id, winner_message, parse_mode="Markdown")

    # **Səsverməni sıfırlayırıq**
    active_voting = None
    vote_timer = None







async def funksiyalar(update: Update, context: CallbackContext):
    """Shows all available commands in the bot, but restricts sensitive commands to a specific user."""
    user_id = update.effective_user.id  # İstifadəçinin ID-sini alırıq

    # **Hər kəs üçün görünən əmrlər**
    commands_list = (
        "🤖 Futbol botunun mövcud əmrləri:\n\n"
        "🚀 `/start` - Botu başladır\n"
        "🛠 `/funksiyalar` - Bütün əmrləri göstərir\n"
        "⚽ `/oyun` - Aktiv oyunun məlumatlarını göstərir\n"
        "👟 `/gelirem` - Oyuna qoşulmaq üçün istifadə olunur\n"
        "💅 `/gelmirem` - Futbola gəlmirəm, evdə dırnağıma lak çəkirəm!\n"
        "📜 `/list` - İştirakçı siyahısını göstərir\n"
        "🔥 `/sesver` - Oyunun ən yaxşı oyunçusuna səs ver (1 saat ərzində)!\n"
        "🏆 `/bitmishoyunlar` - Bütün bitmiş oyunları göstər\n"
        "🆘 `/komek` - Kömək və əlaqə məlumatları\n"

    )
    
    if user_id == GROUP_ADMIN_ID:
        commands_list += (
            "\n🔐 *Şifrəli əmrlər:*\n"
            "📢 `/oyunyarat` - Yeni oyun yaradır\n"
            "🏁 `/oyunubitir` - Oyunu bitir və nəticələri qeyd et\n"
            "🗑 `/oyunusil` - Oyunu sil\n"
            "x `/qrupunidsi` - Qrupun ID-sinə bax\n"
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

    if len(participants) >= 12:
        await query.answer("⚠️ Oyunda maksimum 12 nəfər iştirak edə bilər!", show_alert=True)
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
        await update.message.chat.send_message("❌ Hazırda aktiv oyun yoxdur.")
        return

    game = active_games[chat_id]  # Qrup üçün oyun məlumatlarını götür
    participants = game["participants"]

    # **Əgər istifadəçi artıq siyahıdadırsa, popup alert çıxarırıq**
    if username in participants:
        await update.effective_message.reply_text("⚠️ Siz artıq bu oyunun iştirakçıları arasındasınız!")
        return  # Qrupa heç nə yazmırıq

    if len(participants) >= 12:  # Limit yoxlanışı (14 → 12 dəyişdirildi)
        await update.message.chat.send_message("⚠️ Oyunda maksimum 12 nəfər iştirak edə bilər!")
        return
   
    # **İstifadəçini iştirakçılar siyahısına əlavə edirik**
    participants.add(username)  
    await update.message.chat.send_message(f"✅ {username} oyuna gəlməyini təsdiqlədi!")  # Reply yox, normal mesaj 

    # **Yenilənmiş siyahını göstəririk (bot üçün limit olmadan)**
    await list_participants(update, context, called_by_bot=True)

    # **Əgər iştirakçı sayı 12-ə çatıbsa, avtomatik komandalar qurulsun**
    if len(participants) == 12:
        await komanda_qur(update, context)


    async def mengelmirem(update: Update, context: CallbackContext):
    """Handles a user leaving the game via /mengelmirem command."""
    chat_id = update.effective_chat.id  # Qrupun ID-sini al
    user_id = update.effective_user.id  # İstifadəçinin ID-sini al
    username = update.effective_user.first_name  # İstifadəçinin adını al

    if chat_id not in active_games:  # Qrup üçün aktiv oyun varmı?
        await update.message.chat.send_message("❌ Hazırda aktiv oyun yoxdur.")
        return

    game = active_games[chat_id]  # Qrup üçün oyun məlumatlarını götür
    participants = game["participants"]  # İştirakçıların siyahısını al

    if username not in participants:  # Əgər istifadəçi artıq oyunda deyilsə
        await update.effective_message.reply_text("⚠️ Siz oyunda iştirak etmirsiniz!")
        return  # Qrupa heç nə yazmırıq

    # **İstifadəçini iştirakçılar siyahısından çıxarırıq**
    participants.discard(username)

    # **Bot normal mesaj kimi yazır (reply etmir)**
    await update.message.chat.send_message(f"❌ {username} oyuna gəlməkdən imtina etdi!")

    # **Yenilənmiş siyahını göstəririk (bot üçün limit olmadan)**
    await list_participants(update, context, called_by_bot=True)



def signal_handler(signum, frame):
    logger.info('Signal received, shutting down...')
    exit(0)

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("qrupunidsi", get_chat_id))
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
    application.add_handler(CommandHandler("gelirem", oyunagelirem, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("gelmirem", mengelmirem, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
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
   
    application.add_handler(CallbackQueryHandler(join_game, pattern=r"join_game_\d+"))
    application.add_handler(CallbackQueryHandler(leave_game, pattern=r"leave_game_\d+"))
    application.add_error_handler(error_handler)

    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
