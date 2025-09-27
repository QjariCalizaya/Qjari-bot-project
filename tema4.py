import os
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN") or ""

if not TOKEN:
    raise RuntimeError("there isn't TOKEN in .env")

bot = telebot.TeleBot(TOKEN)

def setup_bot_commands():
    commands = [
        types.BotCommand("start","Запуск"),
        types.BotCommand("help","Помощь"),
        types.BotCommand("about","О боте"),
        types.BotCommand("sum","Сумма чисел"),
        types.BotCommand("echo","Повторить текст"),
    ]

    bot.set_my_commands(commands)


def make_main_kb()->types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("О боте" , "Сумма")
    kb.row("/help")
    return kb

@bot.message_handler(commands=['start' , 'help'])
def start_help(message):
    welcome_text = "Привет!!"


@bot.message_handler(func=lambda m: m.text == "О боте")
def kb_about(m):
    bot.reply_to(m, "я учебный бот: /start, /help, /about, /sum, /echo")


@bot.message_handler(func=lambda m: m.text == "Сумма")
def kb_sum(m):
    bot.send_message(m.chat.id, "Введи числа через пробел или заятую")
    bot.register_next_step_handler(m, on_sum_numbers)

def on_sum_numbers(m):
    nums = parse_ints_from_text(m.text)
    if not nums:
        bot.reply_to(m, "Не вижу чисел. Пример: 2 3 10 или 2, 3, -5")
    else:
        bot.reply_to(m, f"Сумма: {sum(nums)}")


@bot.message_handler(commands=['hide'])
def hide_kb(message):
    rm = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id,"Спрятал клавиатуру." , reply_markup=rm )




if __name__ == "__main__":
 # infinity_polling 4 1>B 15A:>=5G=> >?@0H8205B A5@25@K Telegram =0 =>2K5 A>>1I5=8O
 # skip_pending=True 4 ?@>?CAB8BL «AB0@K5» A>>1I5=8O, =0:>?;5==K5 ?>:0 1>B 1K; 2K:;NG5=
 setup_bot_commands()
 bot.infinity_polling(skip_pending=True)

