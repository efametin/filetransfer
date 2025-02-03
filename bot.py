import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils import executor

# Telegram bot token (bunu öz tokeninlə əvəz et)
TOKEN = "YOUR_BOT_TOKEN"
ADMIN_IDS = {123456789}  # Adminlərin ID-lərini buraya daxil et

# Logger qur
logging.basicConfig(level=logging.INFO)

# Bot və Dispatcher yaradılır
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Parol doğrulama üçün global dəyişən
user_authenticated = {}

# /start komandası
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id

    # Parol yoxlaması
    if user_id not in user_authenticated or not user_authenticated[user_id]:
        await message.answer("🔐 Botu istifadə etmək üçün parol daxil edin:")
        return

    # Parol doğrulaması tamamlanıbsa, digər komandalar işləyə bilər
    await message.answer(
        "⚽ Futbol Matç Botuna xoş gəlmisiniz!\n\n"
        "🔹 Yeni matç yaratmaq üçün yalnız adminlər /createMatch istifadə edə bilər.\n"
        "✅ Oyuna qoşulmaq üçün '+' yazın.\n"
        "❌ Oyundan çıxmaq üçün '-' yazın.\n"
        "📜 Oyunçu siyahısına baxmaq üçün /list yazın.\n"
        "📅 Cari oyun məlumatları üçün /oyun yazın.\n"
        "ℹ Qaydaları öyrənmək üçün /help yazın."
    )

# Parol doğrulama
@dp.message()
async def password_check(message: Message):
    user_id = message.from_user.id
    if user_authenticated.get(user_id, False):
        return  # İstifadəçi artıq autentifikasiya olunub

    if message.text == "777":  # Parol düzgün daxil edildikdə
        user_authenticated[user_id] = True
        await message.answer("✅ Parol uğurla qəbul edildi!\nBot istifadə etməyə başlaya bilərsiniz.")
        await start(message)  # Parol daxil edildikdən sonra start mesajını yenidən göndəririk
        return

    await message.answer("⚠ Daxil etdiyiniz parol yanlışdır! Yenidən cəhd edin.")

# /createMatch komandası
@dp.message(Command("createMatch"))
async def create_match(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Bu əmri yalnız adminlər icra edə bilər!")
        return

    await message.answer("📍 Matç yaradılır... (Bura oyun yaradılma prosesi daxil edilə bilər)")

# /stop komandası - botu dayandırır
@dp.message(Command("stop"))
async def stop(message: Message):
    await message.answer("🛑 Bot dayandırılır...")
    await dp.stop_polling()  # Polling dayandırılır

# /sesver komandası
@dp.message(Command("sesver"))
async def sesver(message: Message):
    await message.answer("🎤 Səsvermə başladı! (Burada səsvermə prosesi daxil edilə bilər.)")

# /elaqe komandası - əlaqə məlumatları
@dp.message(Command("elaqe"))
async def elaqe(message: Message):
    await message.answer("📞 Əlaqə: example@example.com")

# /help komandası - bütün komandaların izahını verir
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

# Botu işə salan əsas funksiya
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
