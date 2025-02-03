import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command

# Telegram bot token (bunu öz tokeninlə əvəz et)
TOKEN = "7675127420:AAFbt7343zQWIBJ9eiwNxpo46yf6DHGf1Kg"
ADMIN_IDS = {1958722880}  # Adminlərin ID-lərini buraya daxil et
PASSWORD = "777"  # Parol

# Logger qur
logging.basicConfig(level=logging.INFO)

# Bot və Dispatcher yaradılır
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Parol doğrulama üçün global dəyişən
user_authenticated = {}

# Helper funksiyalar

def is_user_authenticated(user_id: int) -> bool:
    """İstifadəçinin parol doğrulamasının olub olmadığını yoxlayır."""
    return user_authenticated.get(user_id, False)

def authenticate_user(user_id: int) -> None:
    """İstifadəçini autentifikasiya edir."""
    user_authenticated[user_id] = True

def deauthenticate_user(user_id: int) -> None:
    """İstifadəçini autentifikasiyadan çıxarır."""
    if user_id in user_authenticated:
        del user_authenticated[user_id]

# Komanda funksiyaları

@dp.message(Command("start"))
async def start(message: Message):
    """Botu başlatmaq üçün istifadə edilir."""
    user_id = message.from_user.id

    if not is_user_authenticated(user_id):
        await message.answer("🔐 Botu istifadə etmək üçün parol daxil edin:")
        return

    await message.answer(
        "⚽ Futbol Matç Botuna xoş gəlmisiniz!\n\n"
        "🔹 Yeni matç yaratmaq üçün yalnız adminlər /createMatch istifadə edə bilər.\n"
        "✅ Oyuna qoşulmaq üçün '+' yazın.\n"
        "❌ Oyundan çıxmaq üçün '-' yazın.\n"
        "📜 Oyunçu siyahısına baxmaq üçün /list yazın.\n"
        "📅 Cari oyun məlumatları üçün /oyun yazın.\n"
        "ℹ Qaydaları öyrənmək üçün /help yazın."
    )

@dp.message()
async def password_check(message: Message):
    """Parol yoxlaması edir."""
    user_id = message.from_user.id
    if is_user_authenticated(user_id):
        return  # İstifadəçi artıq autentifikasiya olunub

    if message.text == PASSWORD:  # Parol düzgün daxil edildikdə
        authenticate_user(user_id)
        await message.answer("✅ Parol uğurla qəbul edildi!\nBot istifadə etməyə başlaya bilərsiniz.")
        await start(message)  # Parol daxil edildikdən sonra start mesajını yenidən göndəririk
        return

    await message.answer("⚠ Daxil etdiyiniz parol yanlışdır! Yenidən cəhd edin.")

@dp.message(Command("createMatch"))
async def create_match(message: Message):
    """Yalnız adminlər üçün matç yaratma komandasını işləyir."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Bu əmri yalnız adminlər icra edə bilər!")
        return

    await message.answer("📍 Matç yaradılır... (Bura oyun yaradılma prosesi daxil edilə bilər)")

@dp.message(Command("stop"))
async def stop(message: Message):
    """Botu dayandırır."""
    await message.answer("🛑 Bot dayandırılır...")
    await dp.stop_polling()  # Polling dayandırılır

@dp.message(Command("sesver"))
async def sesver(message: Message):
    """Səsvermə başlatır."""
    await message.answer("🎤 Səsvermə başladı! (Burada səsvermə prosesi daxil edilə bilər.)")

@dp.message(Command("elaqe"))
async def elaqe(message: Message):
    """Əlaqə məlumatlarını təqdim edir."""
    await message.answer("📞 Əlaqə: example@example.com")

@dp.message(Command("help"))
async def show_help(message: Message):
    """Botun istifadə qaydalarını göstərir."""
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
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Botu işə salan zaman səhv baş verdi: {e}")

if __name__ == "__main__":
    asyncio.run(main())  # Kodun başlatılması
