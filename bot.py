import telebot

TOKEN = "8206184834:AAEPOLU65BRFOcmxzTYgLyvzmd_a6klr-qI"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Assalomu alaykum! Men sinov botman 😊")

@bot.message_handler(func=lambda m: True)
def echo_all(message):
    bot.reply_to(message, message.text)

print("Bot ishga tushdi...")
bot.infinity_polling()
