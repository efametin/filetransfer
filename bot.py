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
user_start_times = {}
user_komek_times = {}
user_oyun_times = {}
user_list_times = {}
user_last_stadium_request = {}

active_voting = None  # Hazırda aktiv səsverməni saxlayır
vote_timer = None  # Timer obyektini saxlayır

vote_data = {}

# Bitmiş oyun iştirakçılarını saxlayan dictionary
finished_games_participants = {}

# Bitmiş oyunların siyahısını saxlamaq üçün dictionary
finished_games = []

async def start(update: Update, context: CallbackContext):
    """İstifadəçi `/start` yazanda 24 saatlıq məhdudiyyət tətbiq edən funksiya."""
    
    user_id = update.effective_user.id  # İstifadəçinin Telegram ID-si
    current_time = time.time()  # İndiki vaxt (timestamp)
    
    # **Əgər istifadəçi son dəfə bu əmri yazıbsa və 24 saat keçməyibsə**
    if user_id in user_start_times and (current_time - user_start_times[user_id]) < 86400:  # 86400 saniyə = 24 saat
        try:
            # **Popup mesaj göndəririk (Bot reply etmir, sadəcə alert göstərir)**
            await update.effective_message.reply_text(
                "⚠️ Bu əmri yalnız 24 saat sonra yenidən istifadə edə bilərsiniz!",
                reply_markup={"remove_keyboard": True}
            )
        except Exception as e:
            print(f"Popup mesajı göndərərkən xəta baş verdi: {e}")
        return  # Əmr icra olunmur
    
    # **Əgər 24 saat keçibsə və ya ilk dəfə yazılırsa, əmri icra edirik**
    user_start_times[user_id] = current_time  # Vaxtı yadda saxlayırıq

    # **Botun öz adını alırıq**
    bot_name = context.bot.first_name  

    # **Mesaj məzmunu**
    message = (
        f"Salam {update.effective_user.first_name}! 😊\n"
        f"Mən {bot_name}, qrupumuzda sizi görmək xoşdur! 🎉\n\n"
        f"⚽ Xüsusiyyətlərimi bilmək üçün `/funksiyalar` yaza bilərsən!"
    )

    # **Mesajı qrupa göndəririk**
    await update.message.chat.send_message(message)


async def get_chat_id(update: Update, context: CallbackContext):
    """Bu funksiya istifadəçinin və ya qrupun ID-sini qaytarır."""
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
    if update.message.chat.type != "private":
        await update.message.reply_text("🔒 Bu əmri yalnız mənimlə şəxsi mesajda istifadə edə bilərsən!\n📩 Məni tapıb /oyunyarat yaz.")
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
        f"⚠️ Oyunda iştirak etmək üçün `/oyunagelirem` əmrini, "
        f"iştirak etməkdən imtina üçün `/mengelmirem` əmrini yazın qrupa.\n"
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

    await hamini_chagir(update, context)

    return ConversationHandler.END


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

async def yeni_istifadeci_xos_geldin(update: Update, context: CallbackContext):
    """Qrupa yeni üzv əlavə edilən kimi avtomatik mesaj göndərir."""
    chat_id = update.effective_chat.id  # Qrup ID-si
    new_members = update.message.new_chat_members  # Yeni qoşulan üzvlər

    for member in new_members:
        if member.is_bot:  # Əgər qoşulan botdursa, heç nə etməsin
            continue

        # Yeni üzvün adını və username-nı alırıq
        first_name = member.first_name
        username = f"@{member.username}" if member.username else first_name

        # Mesaj formatı
        message = (
            f"🎉 {username}, aramıza xoş gəldin! 😊\n\n"
            "⚽ Bu futbol qrupunda oyunun təşkil edilməsi prosesi *bot* vasitəsilə tənzimlənir!\n\n"
            "📌 Botun xüsusiyyətlərini öyrənmək üçün `/funksiyalar` əmrini yaza bilərsən! 🔥"
        )

        await context.bot.send_message(chat_id, message, parse_mode="Markdown")


async def delete_game(update: Update, context: CallbackContext):
    """Deletes the created game if the user is the creator."""
    query = update.callback_query
    chat_id = query.from_chat.id

    if chat_id in active_games:
        del active_games[chat_id]
        await query.message.edit_text("🗑️ Oyun uğurla silindi!")
    else:
        await query.answer("Bu oyunu silməyə icazəniz yoxdur!", show_alert=True)

async def oyun(update: Update, context: CallbackContext, called_by_bot=False):
    """İstifadəçi `/oyun` yazanda 5 dəqiqəlik məhdudiyyət tətbiq edən funksiya. 
       Əgər bot özü çağırırsa (`called_by_bot=True`), məhdudiyyət tətbiq olunmur.
    """

    user_id = update.effective_user.id  # İstifadəçinin Telegram ID-si
    chat_id = update.effective_chat.id  # Qrup ID-si
    current_time = time.time()  # İndiki vaxt (timestamp)
    
    # **Əgər əmri bot çağırırsa, 5 dəqiqəlik məhdudiyyəti nəzərə almayaq**
    if not called_by_bot:
        # **İstifadəçi son dəfə bu əmri yazıbsa və 5 dəqiqə keçməyibsə**
        if user_id in user_oyun_times and (current_time - user_oyun_times[user_id]) < 300:  # 300 saniyə = 5 dəqiqə
            await update.effective_message.reply_text(
                "⚠️ Az öncə qrupa bu barədə məlumat göndərmişəm, zəhmət olmasa oyun barədə məlumatı qrupdakı mesajımdan oxu!"
            )
            return  # Əmr icra olunmur

        # **Əgər 5 dəqiqə keçibsə və ya ilk dəfə yazılırsa, istifadəçiyə məhdudiyyət tətbiq olunur**
        user_oyun_times[user_id] = current_time  

    if chat_id not in active_games:
        await update.message.chat.send_message("❌ Hazırda yaradılmış oyun yoxdur.")
        return

    game = active_games[chat_id]
    game_info = (
        f"⚽ Gələcək Futbol Oyunumuz ⚽\n"
        f"📍 Oyunun yeri: {game['location']}\n"
        f"⏰ Başlama vaxtı: {game['time']}\n"
        f"📄 Əlavə məlumat: {game['extra_info']}\n\n"
        f"Bu oyunda səni görmək xoş olar. Oyuna gəlmək istəsən `/gelirem` yazaraq matça qoşula bilərsən! ⚽"
    )

    # **Mesajı reply etmədən, normal mesaj kimi göndəririk**
    await update.message.chat.send_message(game_info, parse_mode="Markdown")


match_location = None

# Şəxsi mesajda şifrə tələb edən mərhələlər
PASSWORD_STAGE, LOCATION_STAGE = range(2)

async def matchinyeri(update: Update, context: CallbackContext):
    """Qrupda çağırılsa, reply olaraq şəxsi mesajda çağırılmalı olduğunu bildirir."""
    if update.effective_chat.type != "private":
        await update.message.reply_text("⚠️ Bu əmri yalnız şəxsi mesajda istifadə edə bilərsiniz!", reply_to_message_id=update.message.message_id)
        return

    await update.message.reply_text("🔑 Stadion yerini əlavə etmək üçün şifrəni daxil edin:")
    return PASSWORD_STAGE

async def check_match_password(update: Update, context: CallbackContext):
    """Şifrəni yoxlayır və stadion linkini tələb edir."""
    if update.message.text != GAME_CREATION_PASSWORD:
        await update.message.reply_text("❌ Şifrə yalnışdır! Yenidən cəhd edin.")
        return ConversationHandler.END

    await update.message.reply_text("📍 Oyunun keçiriləcəyi stadionun Google Maps linkini göndərin:")
    return LOCATION_STAGE

async def set_match_location(update: Update, context: CallbackContext):
    """Google Maps linkini yadda saxlayır."""
    global match_location
    match_location = update.message.text  # Linki yadda saxlayırıq

    await update.message.reply_text("✅ Stadionun yeri uğurla qeyd edildi!")
    return ConversationHandler.END

async def hamini_chagir(update: Update, context: CallbackContext):
    """Qrupdakı bütün istifadəçiləri işarələyərək yeni matç barədə məlumat göndərir."""
    chat_id = update.effective_chat.id  # Qrup ID-si

    # Qrupun üzvlərini gətir (bu botun admin olması lazımdır!)
    try:
        chat_members = await context.bot.get_chat_administrators(chat_id)  # Adminləri götürürük (bütün user-ləri götürmək olmur)
        user_mentions = " ".join([f"@{admin.user.username}" for admin in chat_members if admin.user.username])  # Adminləri tag edirik
    except Exception as e:
        user_mentions = "📢 Qrup üzvləri"

    # Mesaj formatı
    message = (
        f"{user_mentions}\n\n"
        "📢 *Dəyərli qrup üzvləri,* yeni matç yaradılıb! 🎉\n\n"
        "⚽ Bu matçda iştirak edib-etməyəcəyinizi qeyd edin!\n\n"
        "✅ Oyunda iştirak üçün qrupa `/gelirem` yazaraq iştirakçılar listinə qoşula bilərsiniz!\n"
        "❌ Əgər oyuna qoşulub, sonradan gəlmək istəməsəniz, `/gelmirem` yazaraq matçdan çıxa bilərsiniz.\n\n"
        "⚡ Hamının cavabını gözləyirəm!"
    )

    await context.bot.send_message(chat_id, message, parse_mode="Markdown")
  
async def stadionunyeri(update: Update, context: CallbackContext):
    """Oyun stadionunun yerini paylaşır, lakin istifadəçilər 10 dəqiqədə bir dəfə çağıra bilər."""
    global match_location
    user_id = update.effective_user.id  # İstifadəçi ID-si
    chat_id = update.effective_chat.id  # Qrup ID-si
    current_time = time.time()  # İndiki vaxt (timestamp)

    # Əgər oyun yeri qeyd olunmayıbsa
    if not match_location:
        await update.message.chat.send_message("❌ Oyunun stadion yeri hələ qeyd edilməyib.")
        return

    # Əgər istifadəçi 10 dəqiqədən tez çağırırsa, popup alert çıxar
    if user_id in user_last_stadium_request and (current_time - user_last_stadium_request[user_id]) < 600:  # 600 saniyə = 10 dəqiqə
        await update.effective_message.reply_text("⚠️ Stadionun yerini artıq paylaşmışam. 10 dəqiqə sonra yenidən yoxlaya bilərsən!", show_alert=True)
        return

    # Əgər 10 dəqiqə keçibsə və ya ilk dəfə çağırılırsa, vaxtı yadda saxlayırıq
    user_last_stadium_request[user_id] = current_time

    stadium_message = (
        "📍 *Növbəti matçımızın keçiriləcəyi stadionun ünvanı:*\n"
        f"{match_location}\n\n"
        "📌 Google Maps üzərindən baxmaq üçün linkə klikləyə bilərsiniz!"
    )

    await update.message.chat.send_message(stadium_message, parse_mode="Markdown")


async def komek(update: Update, context: CallbackContext):
    """İstifadəçi `/komek` yazanda 1 saatlıq məhdudiyyət tətbiq edən funksiya."""
    
    user_id = update.effective_user.id  # İstifadəçinin Telegram ID-si
    current_time = time.time()  # İndiki vaxt (timestamp)
    
    # **Əgər istifadəçi son dəfə bu əmri yazıbsa və 1 saat keçməyibsə**
    if user_id in user_komek_times and (current_time - user_komek_times[user_id]) < 3600:  # 3600 saniyə = 1 saat
        await update.effective_message.reply_text(
            "⚠️ Bu əmri daha öncə istifadə etmisən. Cavaba bax və ya 1 saat sonra yenidən kömək istə!",
        )
        return  # Əmr icra olunmur
    
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
        f"[whatsApp]-dan({whatsapp_link}) yazaraq və ya [zəng]({call_link}) edərək əlaqə saxlaya bilərsən. 📞"
    )

    # **Mesajı Markdown formatında göndəririk**
    await update.message.chat.send_message(help_text, parse_mode="Markdown")

async def list_participants(update: Update, context: CallbackContext, called_by_bot=False):
    """Lists all participants of the current game. If called_by_bot=True, it bypasses the cooldown."""
    
    user_id = update.effective_user.id  # İstifadəçinin Telegram ID-si
    chat_id = update.effective_chat.id  # Qrupun ID-sini al
    current_time = time.time()  # İndiki vaxt (timestamp)
    
    # **Əgər funksiya istifadəçi tərəfindən çağırılırsa və 5 dəqiqə keçməyibsə**
    if not called_by_bot and user_id in user_list_times and (current_time - user_list_times[user_id]) < 300:  # 300 saniyə = 5 dəqiqə
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


async def oyunubitir(update: Update, context: CallbackContext):
    """Aktiv oyunu bitirmək üçün şifrə tələb edir və qalib komandanı müəyyənləşdirir."""
    chat_id = update.effective_chat.id  # Qrupun ID-sini al

    if chat_id not in active_games:  # Əgər aktiv oyun yoxdursa
        await update.message.reply_text("❌ Hazırda bitiriləcək aktiv oyun yoxdur.")
        return

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
            f"-------------------------\n"
        )

    await update.message.reply_text(result_text)



async def sesver(update: Update, context: CallbackContext):
    """Aktiv səsverməni göstərir və istifadəçilərə səs verməyə icazə verir."""
    global active_voting

    if not active_voting:
        await update.message.chat.send_message("❌ Hazırda aktiv səsvermə yoxdur.")
        return

    chat_id = active_voting["chat_id"]
    if update.effective_chat.id != chat_id:
        await update.message.chat.send_message("❌ Bu səsvermə başqa bir oyun üçündür.")
        return

    keyboard = []
    for participant in active_voting["participants"]:
        vote_count = sum(1 for v in active_voting["votes"].values() if v == participant)
        button_text = f"{participant} - {vote_count} səs"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"vote_{participant}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.chat.send_message("🗳 *Oyunun ən yaxşı oyunçusunu (Man of the Match) seçmək üçün səs verin!*", 
                                           reply_markup=reply_markup, parse_mode="Markdown")




async def vote_handler(update: Update, context: CallbackContext):
    """İstifadəçinin səsini qeydə alır və yenilənmiş nəticələri göstərir."""
    global active_voting

    query = update.callback_query
    voter = query.from_user.first_name  # Səs verən istifadəçinin adı
    voter_id = query.from_user.id  # Səs verən istifadəçinin ID-si
    selected_player = query.data.split("_")[-1]  # Seçilən oyunçu

    if not active_voting:
        await query.answer("❌ Hazırda aktiv səsvermə yoxdur!", show_alert=True)
        return

    if voter in active_voting["votes"]:
        await query.answer("❌ Siz artıq səs vermisiniz!", show_alert=True)
        return

    # **Əgər istifadəçi özünə səs verirsə, icazə vermirik**
    if voter == selected_player:
        await query.answer("⚠️ Özünə səs vermək olmaz!", show_alert=True)
        return

    # **Əgər başqasına səs verirsə, popup çıxır: "Hə" və "Yox" düymələri ilə**
    keyboard = [
        [
            InlineKeyboardButton("✅ Hə", callback_data=f"confirm_vote_{selected_player}_{voter_id}"),
            InlineKeyboardButton("❌ Yox", callback_data=f"cancel_vote_{voter_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.answer()  # Popupu bağlamaq üçün boş cavab veririk
    await query.message.reply_text(
        f"⚡ {voter}, {selected_player} oyunçusuna səs verməyə əminsən?",
        reply_markup=reply_markup
    )



async def confirm_vote(update: Update, context: CallbackContext):
    """İstifadəçi 'Hə' düyməsini seçəndə səsi qeydə alır."""
    global active_voting

    query = update.callback_query
    data = query.data.split("_")
    selected_player = data[2]  # Səs verilən oyunçu
    voter_id = int(data[3])  # Səs verən istifadəçi ID-si

    if not active_voting:
        await query.answer("❌ Səsvermə artıq aktiv deyil!", show_alert=True)
        return

    active_voting["votes"][voter_id] = selected_player  # Səsi qeydə alırıq

    # **Yenilənmiş səs saylarını hesablamaq üçün**
    keyboard = []
    for participant in active_voting["participants"]:
        vote_count = sum(1 for v in active_voting["votes"].values() if v == participant)
        button_text = f"{participant} - {vote_count} səs"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"vote_{participant}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text("🗳 Oyunun ən yaxşı oyunçusuna səs verin!", reply_markup=reply_markup)
    await query.answer("✅ Səsiniz qeydə alındı!")


async def cancel_vote(update: Update, context: CallbackContext):
    """İstifadəçi 'Yox' düyməsini seçəndə səsvermədən imtina edir."""
    query = update.callback_query
    await query.answer("🚫 Səsvermədən imtina etdiniz!", show_alert=True)
    await query.message.delete()  # Popup mesajını silirik



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

    # **Qalib mesajı daha diqqətçəkən olsun**
    winner_message = (
        "🏆🔥 *SON OYUNUN ƏN YAXŞI OYUNÇUSU!* 🔥🏆\n\n"
        f"🎖 *Man of the Match:* **{winner}** 🎖\n\n"
        "👏 Təbriklər! Oyunda əla performans göstərdin! 👏\n\n"
        "⚽ Səs verən hər kəsə təşəkkürlər! 🙌\n"
        "🚀 Gələcək oyunlarda uğurlar!"
    )

    # **Mesajı qrupa göndəririk**
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
        "👟 `/oyunagelirem` - Oyuna qoşulmaq üçün istifadə olunur\n"
        "💅 `/mengelmirem` - Futbola gəlmirəm, evdə dırnağıma lak çəkirəm!\n"
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
            "🗑 `/qrupunidsi` - Qrupun ID-sinə bax\n"
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

    # **Əgər iştirakçı sayı 12-ə çatıbsa, avtomatik komandalar qurulsun**
    if len(participants) == 12:
        await komanda_qur(update, context)

    # **Yenilənmiş siyahını göstəririk (bot üçün limit olmadan)**
    await list_participants(update, context, called_by_bot=True)


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
    application.add_handler(CommandHandler("stadionunyeri", stadionunyeri, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))


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
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, yeni_istifadeci_xos_geldin))
    application.add_handler(CommandHandler("list", list_participants, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("funksiyalar", funksiyalar, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("komek", komek, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("sesver", sesver, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("oyunagelirem", oyunagelirem, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("mengelmirem", mengelmirem, filters=filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CallbackQueryHandler(vote_handler, pattern=r"vote_.*"))
    application.add_handler(CallbackQueryHandler(confirm_vote, pattern=r"confirm_vote_.*"))
    application.add_handler(CallbackQueryHandler(cancel_vote, pattern=r"cancel_vote_.*"))

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
