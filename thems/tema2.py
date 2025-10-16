import os
from dotenv import load_dotenv
import telebot
from telebot import types
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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

""" @bot.message_handler(commands = ['start','help'])
def start_help(message):
    bot.send_message(
        message.chat.id,
        "Привет!! Доступно: /about, /sum, /echo"
    ) """

@bot.message_handler(commands=['about'])
def about(message):
    bot.reply_to(   message,
                    "Я учебный бот. Команды:"
                    "/start, /help, /about, /sum, /echo"
                 )

@bot.message_handler(commands=['echo'])
def echo_cmd(message):
    parts = message.text.split(maxsplit=1)

    if len(parts)<2 or not parts[1].strip():
        bot.reply_to(message, "Пример: /echo Привет , мир")
    else:
        bot.reply_to(message,parts[1])

def parse_ints_from_text(text:str) -> list[int]:
    text = text.replace(",", " ")
    tokens = [t for t in text.split() if not t.startswith("/")]
    return [int(t) for t in tokens if t.strip().lstrip("-").isdigit()]

""" @bot.message_handler(commands=['sum'])
def cmd_sum(message):
    nums = parse_ints_from_text(message.text)

    if not nums:
        bot.reply_to(
            message,
            "Нужно написать числа. Пример: /sum 2 3 10 или 2, 3 , -5"
        )
    else:
        bot.reply_to(message,f"Сумма: {sum(nums)}") """


def make_main_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("О боте" , "Сумма")
    keyboard.row("/help")
    return keyboard

@bot.message_handler(commands=['start','help'])
def start_help(message):
    bot.send_message(
        message.chat.id,
        "Привет! доступно: /about, /sum , /echo , \nИли пользуйтесь кнопками",
        reply_markup=make_main_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == "О боте")
def kb_about(message):
    about(message)

@bot.message_handler(func=lambda m: m.text == "Сумма")
def kb_sum(message):
    bot.send_message(message.chat.id,
                     "Введите числа через пробел или запятую:")
    bot.register_next_step_handler(message, on_sum_numbers)

def on_sum_numbers(message):
    nums = parse_ints_from_text(message.text)
    if not nums:
        bot.reply_to(message, "Не вижу чисел. Пример: 2 3 10")
    else:
        bot.reply_to(message, f"Сумма {sum(nums)}")

@bot.message_handler(commands = ['hide'])
def hide_kb(message):
    rm = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        "Спрятал клавиатуру",
        reply_markup=rm
    )


@bot.message_handler(commands=['confirm'])
def confirm_cmd(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("Да", callback_data="confirm:yes"),
        types.InlineKeyboardButton("Нет", callback_data="confirm:no")
    )
    bot.send_message(message.chat.id, "Понравился пример?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm:"))
def on_confirm(c):
    choice = c.data.split(":",1 )[1]
    bot.answer_callback_query(c.id, "Спасибо!")
    bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=None)

    response = "Отлично!" if choice == "yes" else "Окей, улучшим!"
    bot.send_message(c.message.chat.id, response)

@bot.message_handler(commands=['sum'])
def cmd_sum(m):
    logging.info(f"Sum command from{m.from_user.first_name}")
    nums = parse_ints_from_text(m.text)
    logging.info(f"Parsed numbers:{nums}")
    bot.send_message(m.chat.id, f"сумма: {sum(nums)}")



if __name__ == "__main__":
 # infinity_polling 4 1>B 15A:>=5G=> >?@0H8205B A5@25@K Telegram =0 =>2K5 A>>1I5=8O
 # skip_pending=True 4 ?@>?CAB8BL «AB0@K5» A>>1I5=8O, =0:>?;5==K5 ?>:0 1>B 1K; 2K:;NG5=
 setup_bot_commands()
 bot.infinity_polling(skip_pending=True)