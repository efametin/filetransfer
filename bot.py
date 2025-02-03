from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# /start əmri
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hazırlanır...')

# /stop əmri - Botu dayandırır
async def stop(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Bot dayandırıldı.')
    await context.application.stop()

# /create əmri
async def create(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hazırlanır...')

# /vote əmri
async def vote(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hazırlanır...')

# /list əmri
async def list(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hazırlanır...')

# /help əmri - Botun əmr siyahısını göstərir
async def help(update: Update, context: CallbackContext) -> None:
    help_text = (
        "Əmrlər:\n"
        "/start - Botu başlat\n"
        "/stop - Botu dayandır\n"
        "/create - Yeni yaradılacaq obyekt\n"
        "/vote - Səs vermək\n"
        "/list - Mövcud siyahını göstər\n"
        "/help - Yardım və əmrlər siyahısını göstər"
    )
    await update.message.reply_text(help_text)

async def main() -> None:
    # Tokeni daxil edin
    application = Application.builder().token("7675127420:AAFbt7343zQWIBJ9eiwNxpo46yf6DHGf1Kg").build()

    # Əmrləri əlavə edin
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("create", create))
    application.add_handler(CommandHandler("vote", vote))
    application.add_handler(CommandHandler("list", list))
    application.add_handler(CommandHandler("help", help))  # /help əmri əlavə olundu

    # Botu işə salın
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
