import nest_asyncio
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime, timedelta

# Telegram bot token (bunu öz tokeninlə əvəz et)
TOKEN = "7675127420:AAFbt7343zQWIBJ9eiwNxpo46yf6DHGf1Kg"

# Admin ID-ləri (buraya öz Telegram ID-lərinizi əlavə edin)
ADMIN_IDS = {1958722880}  # Buraya adminlərin ID-lərini daxil et

# Logger qur
logging.basicConfig(level=logging.INFO)

# Bot və Dispatcher yaradılır
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Oyunçuların siyahısı və cari oyun məlumatları
players_list = []
match_info = None  # Cari oyun məlumatları burda saxlanır
match_message_id = None  # Oyun mesajının ID-sini saxlamaq üçün

# /start komandası
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "⚽ Futbol Matç Botuna xoş gəlmisiniz!\n\n"
        "🔹 Yeni matç yaratmaq üçün yalnız adminlər /create_match istifadə edə bilər.\n"
        "✅ Oyuna qoşulmaq üçün '+' yazın.\n"
        "❌ Oyundan çıxmaq üçün '-' yazın.\n"
        "📜 Oyunçu siyahısına baxmaq üçün /list yazın.\n"
        "📅 Cari oyun məlumatları üçün /oyun yazın.\n"
        "ℹ Qaydaları öyrənmək üçün /help yazın."
    )

# 🛑 Yalnız adminlər matç yarada bilər
@dp.message(Command("create_match"))
async def create_match(message: Message):
    global match_info

    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Bu əmri yalnız adminlər icra edə bilər!")
        return

    match_info = {"location": "", "date_time": None, "notes": ""}
    await message.answer("📍 Oyunun ünvanını göndərin:")

# Ünvanı qəbul edirik
@dp.message()
async def match_details(message: Message):
    global match_info, players_list, match_message_id

    user_id = message.from_user.id
    user_name = message.from_user.full_name
    text = message.text.strip()

    if match_info and not match_info["location"]:
        match_info["location"] = text
        await message.answer("🕒 Oyunun saatını (YYYY-MM-DD HH:MM) formatında yazın:")
        return

    if match_info and not match_info["date_time"]:
        try:
            game_date = datetime.strptime(text, "%Y-%m-%d %H:%M")
            if game_date < datetime.now() + timedelta(days=1):
                await message.answer("⚠ Oyun yalnız sabah və ya daha sonraki tarixlər üçün yaradıla bilər.")
                return
            match_info["date_time"] = game_date
            await message.answer("📝 Oyunun əlavə qeydlərini daxil edin:")
        except ValueError:
            await message.answer("⚠ Tarixi düzgün formatda daxil edin (YYYY-MM-DD HH:MM).")
        return

    if match_info and not match_info["notes"]:
        match_info["notes"] = text

        # ❌ Sil düyməsi olan inline keyboard yaradılır
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Oyunu sil", callback_data="delete_match")]
        ])

        sent_message = await message.answer(
            f"✅ Yeni matç yaradıldı!\n\n📍 Ünvan: {match_info['location']}\n"
            f"🕒 Vaxt: {match_info['date_time'].strftime('%Y-%m-%d %H:%M')}\n📝 Qeyd: {match_info['notes']}",
            reply_markup=keyboard
        )

        match_message_id = sent_message.message_id  # Mesajın ID-sini saxla
        return

    # "+" və "-" ilə oyunçu siyahısını idarə etmək
    if text == "+" or text == "-":
        if match_info and match_info["date_time"]:
            time_left = match_info["date_time"] - datetime.now()
            if time_left <= timedelta(hours=1):
                await message.answer("⛔ Oyun tarixinə 1 saat qaldığı üçün siyahıya qoşulmaq/çıxmaq mümkün deyil!")
                return

        if text == "+":
            if user_name not in players_list:
                players_list.append(user_name)
                await bot.send_message(
                    message.chat.id,
                    f"✅ {user_name} oyuna qoşuldu!\n\n{get_player_list_text()}"
                )
            else:
                await message.answer(f"⚠ {user_name} artıq siyahıdadır!")

        elif text == "-":
            if user_name in players_list:
                players_list.remove(user_name)
                await bot.send_message(
                    message.chat.id,
                    f"❌ {user_name} oyundan çıxdı!\n\n{get_player_list_text()}"
                )
            else:
                await message.answer(f"⚠ {user_name} siyahıda yoxdur!")

# /list komandası - cari oyunçular siyahısını göstərir
@dp.message(Command("list"))
async def show_players(message: Message):
    await message.answer(get_player_list_text())

# /oyun komandası - cari matç məlumatını göstərir
@dp.message(Command("oyun"))
async def show_match(message: Message):
    if match_info and match_info["date_time"]:
        await message.answer(
            f"📍 Oyun Məlumatları:\n"
            f"📌 Ünvan: {match_info['location']}\n"
            f"🕒 Vaxt: {match_info['date_time'].strftime('%Y-%m-%d %H:%M')}\n"
            f"📝 Qeyd: {match_info['notes']}"
        )
    else:
        await message.answer("❌ Hələ ki oyun yoxdur.")

# /help komandası - qaydaları göstərir
@dp.message(Command("help"))
async def show_help(message: Message):
    await message.answer(
        "ℹ **Futbol Matç Bot Qaydaları:**\n\n"
        "✅ **Oyuna qoşulmaq üçün:** + yazın.\n"
        "❌ **Oyundan çıxmaq üçün:** - yazın.\n"
        "📜 **Oyunçu siyahısını görmək üçün:** /list yazın.\n"
        "📅 **Cari oyun məlumatını görmək üçün:** /oyun yazın.\n"
        "⛔ **Oyun tarixinə 1 saat qalmış siyahıya qoşulmaq mümkün deyil.**\n"
        "🛑 **Yalnız adminlər matç yarada bilər.**"
    )

# Oyunu silmək üçün callback
@dp.callback_query(lambda c: c.data == "delete_match")
async def delete_match(callback_query: types.CallbackQuery):
    global match_info, players_list, match_message_id

    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("⛔ Bu əmri yalnız adminlər icra edə bilər!", show_alert=True)
        return

    match_info = None
    players_list.clear()
    await bot.delete_message(callback_query.message.chat.id, match_message_id)
    await callback_query.message.answer("❌ Oyun silindi!")

# Helper funksiya - oyunçu siyahısını qaytarır
def get_player_list_text():
    return "📜 Cari oyunçular siyahısı:\n" + "\n".join(f"🔹 {player}" for player in players_list) if players_list else "🚫 Siyahıda heç kim yoxdur."

nest_asyncio.apply()
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

loop = asyncio.get_event_loop()
loop.create_task(main()) 
