from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# /start əmri
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hazırlanır...')

# /stop əmri - Botu dayandırır
def stop(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Bot dayandırıldı.')
    context.application.stop()

# /create əmri
def create(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hazırlanır...')

# /vote əmri
def vote(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hazırlanır...')

# /list əmri
def list(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hazırlanır...')

# /help əmri - Botun əmr siyahısını göstərir
def help(update: Update, context: CallbackContext) -> None:
    help_text = (
        "Əmrlər:\n"
        "/start - Botu başlat\n"
        "/stop - Botu dayandır\n"
        "/create - Yeni yaradılacaq obyekt\n"
        "/vote - Səs vermək\n"
        "/list - Mövcud siyahını göstər\n"
        "/help - Yardım və əmrlər siyahısını göstər"
    )
    update.message.reply_text(help_text)

def main() -> None:
    # Tokeni daxil edin
    updater = Updater("7675127420:AAFbt7343zQWIBJ9eiwNxpo46yf6DHGf1Kg")

    # Dispatcher əldə edin
    dispatcher = updater.dispatcher

    # Əmrləri əlavə edin
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("stop", stop))
    dispatcher.add_handler(CommandHandler("create", create))
    dispatcher.add_handler(CommandHandler("vote", vote))
    dispatcher.add_handler(CommandHandler("list", list))
    dispatcher.add_handler(CommandHandler("help", help))  # /help əmri əlavə olundu

    # Botu işə salın
    updater.start_polling()

    # Botu dayandırmaq üçün
    updater.idle()

if __name__ == '__main__':
    main()
