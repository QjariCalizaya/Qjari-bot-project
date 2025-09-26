import os
from dotenv import load_dotenv # G8B05B ?5@5<5==K5 87 D09;0 .env
import telebot # A8=E@>==0O 181;8>B5:0 4;O Telegram Bot API
# 1) 
load_dotenv()
TOKEN = os.getenv("TOKEN") # 2 .env 4>;65= 1KBL TOKEN=... (?>;CG8BL C @BotFather)
if not TOKEN:
 raise RuntimeError("not found TOKEN in .env.  and add TOKEN=...")
# 2) %>740U< >1J5:B 1>B0
bot = telebot.TeleBot(TOKEN) # 745AL =0AB@08205BAO ?>4:;NG5=85 : Bot API
# 3)
@bot.message_handler(commands=['start'])
def start(message):
 # message - output message
 bot.reply_to(
 message,
 "Привет!! Я живой"
 "Команды: /start, /help"
 )
# 4) 
@bot.message_handler(commands=['help'])
def help_cmd(message):
 bot.reply_to(
 message,
 "/start - начать диалог"
 "/help - показать подсказку"
 )
# 5) 
if __name__ == "__main__":
 # infinity_polling 4 1>B 15A:>=5G=> >?@0H8205B A5@25@K Telegram =0 =>2K5 A>>1I5=8O
 # skip_pending=True 4 ?@>?CAB8BL «AB0@K5» A>>1I5=8O, =0:>?;5==K5 ?>:0 1>B 1K; 2K:;NG5=
 bot.infinity_polling(skip_pending=True)