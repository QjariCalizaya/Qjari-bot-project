# Implement a /max command, which also handles parsing. The answer should be in the form: "Maximum: X"
# Add buttons: /about, /sum, /hide, /show
# Create a /confirm command with a different answer for each choice
# Update README.md: "How to run", "List of commands"
# Make meaningful commits and push to GitHub
# Think about and determine the topic of the final project

from dotenv import load_dotenv
import telebot
import os
from telebot import types

load_dotenv()
TOKEN = os.getenv("TOKEN") or ""

if not TOKEN:
    raise RuntimeError("there isn't TOKEN in .env")

bot = telebot.TeleBot(TOKEN)


def setup_bot_commands():
    commands = [
        types.BotCommand("about", "О боте"),
        types.BotCommand("sum", "Сумма чисел"),
        types.BotCommand("max", "Максимальное число"),
        types.BotCommand("hide", "Скрыть меню"),
        types.BotCommand("show", "Показать меню"),
    ]
    bot.set_my_commands(commands)

def make_main_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row( "О боте")
    keyboard.row("Сумма чисел" , "Максимальное число")
    keyboard.row("Скрыть меню" , "Показать меню" )
    return keyboard

def parse_ints_from_text(text: str) -> list[int]:
    text = text.replace(",", " ")
    tokens = [t for t in text.split() if not t.startswith("/")]
    result = []
    for t in tokens:
        t = t.strip()
        if t.isdigit() or (t.startswith("-") and t[1:].isdigit()):
            result.append(int(t))
    return result


def on_sum_numbers(message):
    nums = parse_ints_from_text(message.text)
    if not nums:
        bot.reply_to(message, "не вижу чисел, Пример: 1 5 2 10 или 2 , 5 , -5")
    else:
        bot.reply_to(message, f"Сумма: {sum(nums)}")

def maximun_number(message):
    nums = parse_ints_from_text(message.text)
    if not nums:
        bot.reply_to(message, "не вижу чисел, Пример: 1 5 2 10 или 2 , 5 , -5")
    else:
        bot.reply_to(message, f"Max: {sorted(nums,reverse=True)[0]} ")

def ask_confirmation(chat_id, action: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("Да", callback_data=f"confirm:{action}:yes"),
        types.InlineKeyboardButton("Нет", callback_data=f"confirm:{action}:no")
    )
    bot.send_message(chat_id, f"Вы уверены, что хотите выполнить '{action}'?", reply_markup=kb)




@bot.message_handler(commands=['show', 'start'])
def start(message):
   bot.send_message(message.chat.id,
                    "Привет, я учебный бот, что вы хотите делать?",
                    reply_markup=make_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "Показать меню")
def start(message):
   bot.send_message(message.chat.id,
                    "Привет, я учебный бот, что вы хотите делать?",
                    reply_markup=make_main_keyboard())




@bot.message_handler(commands=["about"])
def about_command(message):
   bot.reply_to(message, "Привет, я Qbot, учебный бот, смотрите список команд в меню или напишите /show")

@bot.message_handler(func=lambda m: m.text == "О боте")
def about_button(message):
   bot.reply_to(message, "Привет, я Qbot, учебный бот, смотрите список команд в меню или напишите /show")


@bot.message_handler(commands=["sum"])
def sumNumbers_command(message):
    ask_confirmation(message.chat.id, "sum")

@bot.message_handler(func=lambda m: m.text == "Сумма чисел")
def sumNumbers_button(message):
    ask_confirmation(message.chat.id, "sum")


@bot.message_handler(commands=["max"])
def max_command(message):
    ask_confirmation(message.chat.id, "max")

@bot.message_handler(func=lambda m: m.text == "Максимальное число")
def max_button(message):
    ask_confirmation(message.chat.id, "max")


@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm:"))
def on_confirm(c):
    _, action, choice = c.data.split(":")  # ejemplo: confirm:sum:yes
    bot.answer_callback_query(c.id)  # cierra la ruedita de carga en Telegram
    
    if choice == "yes":
        if action == "sum":
            bot.send_message(c.message.chat.id, "Ок, введи числа для суммы:")
            bot.register_next_step_handler(c.message, on_sum_numbers)
        elif action == "max":
            bot.send_message(c.message.chat.id, "Ок, введи числа для поиска максимума:")
            bot.register_next_step_handler(c.message, maximun_number)
    else:
        bot.send_message(c.message.chat.id, f"Действие '{action}' отменено.")





@bot.message_handler(commands=['hide'])
def hide_kb(message):
    rm = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id,"Спрятал клавиатуру." , reply_markup=rm )

@bot.message_handler(func=lambda m:m.text == "Скрыть меню")
def hide_kb(message):
    rm = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id,"Спрятал клавиатуру." , reply_markup=rm )


 

if __name__ == "__main__":
 # infinity_polling 4 1>B 15A:>=5G=> >?@0H8205B A5@25@K Telegram =0 =>2K5 A>>1I5=8O
 # skip_pending=True 4 ?@>?CAB8BL «AB0@K5» A>>1I5=8O, =0:>?;5==K5 ?>:0 1>B 1K; 2K:;NG5=
 setup_bot_commands() 
 bot.infinity_polling(skip_pending=True)
