import os
import telebot
from telebot import types
from dotenv import load_dotenv
import logging
from db import *

load_dotenv()
TOKEN = os.getenv("TOKEN") or ""

init_db()

def parse_ints_from_text(text:str) -> list[int]:
    text = text.replace(",", " ")
    tokens = [t for t in text.split() if not t.startswith("/")]
    return [int(t) for t in tokens if t.strip().lstrip("-").isdigit()]

if not TOKEN:
    raise RuntimeError("there isn't TOKEN in .env")

bot = telebot.TeleBot(TOKEN)


def setup_bot_commands():
    commands = [
        types.BotCommand("start","Запуск"),
        types.BotCommand("note_add","add"),
        types.BotCommand("note_list","show"),
        types.BotCommand("note_find","find"),
        types.BotCommand("note_edit","edit"),
        types.BotCommand("note_de","delete"), 
        types.BotCommand("note_count","count"), 
        types.BotCommand("activity","activity"),

    ]

    bot.set_my_commands(commands)


""" def make_main_kb()->types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("О боте" , "Сумма")
    kb.row("/help")
    return kb """

# функция запуска
@bot.message_handler(commands=['start' , 'help'])
def start_help(message):
    welcome_text = "Привет!!, я учебный бот который сохраняет список"
    bot.reply_to(message,welcome_text)


# функция для добавления заметки
@bot.message_handler(commands=['note_add'])
def note_add(message):

    if(count_note(message.from_user.id) > 6 ):
        bot.send_message(message.chat.id, "ты уже достиг лимит 50 записей")
    else:
        bot.send_message(message.chat.id, "Введи текст заметки")
        bot.register_next_step_handler(message, save_note)

# функция для сохранения заметки и обратной связи
def save_note(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if not text:
        bot.reply_to(message, "Текст пустой, попробуй снова.")
        return

    note_id = add_note(user_id, text) 
    bot.reply_to(message, f"Заметка сохранена (id={note_id})" )


# функция для возвращения всех заметок
@bot.message_handler(commands=['note_list'])
def note_list(message):
    note = list_notes(message.from_user.id)
    text = ""
    for note_id, note_text, created_at in note:
        text += f"\n[{note_id}] {note_text} ({created_at})"

    bot.send_message(message.chat.id, text )


# функция для поиска заметки по слову
@bot.message_handler(commands=['note_find'])
def note_find(message):
    bot.send_message(message.chat.id, "введи текст для поиска")
    bot.register_next_step_handler(message,find )

def find(message):
    note = find_notes(message.from_user.id , message.text)
    text = ""
    for note_id, note_text, created_at in note:
        text += f"\n[{note_id}] {note_text} ({created_at})"

    bot.send_message(message.chat.id, text)


# функция для замены заметки по ID и новому тексту
@bot.message_handler(commands=['note_edit'])
def note_edit(message):
    bot.send_message(message.chat.id, "Введи ID заметки, которую хочешь изменить")
    bot.register_next_step_handler(message, edit_step)

# обратная связь при редактировании
def edit_step(message):
    user_id = message.from_user.id
    try:
        note_id = int(message.text.strip())
    except ValueError:
        bot.reply_to(message, "ID должен быть числом")
        return
    
    bot.send_message(message.chat.id, "Введи новый текст")
    bot.register_next_step_handler(message, update_step, note_id)


def update_step(message, note_id):
    user_id = message.from_user.id
    new_text = message.text.strip()

    if not new_text:
        bot.reply_to(message, "Текст пустой")
        return

    if update_note(user_id, note_id, new_text):
        bot.reply_to(message, f"Заметка {note_id} обновлена")
    else:
        bot.reply_to(message, "Не удалось обновить заметку (проверь ID)")



# функция для удаления заметки
@bot.message_handler(commands=['note_de'])
def note_delete(message):
    bot.send_message(message.chat.id, "введите ID")
    bot.register_next_step_handler(message,delete )

def delete(message):
    userID = message.from_user.id
    try:
        note_id = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "ID должен быть числом")
        return
    if delete_note(userID, note_id):
        bot.send_message(message.chat.id, "Заметка удалена")
    else:
        bot.send_message(message.chat.id, "Не удалось удалить заметку")

# функция чтобы узнать сколько у тебя заметок
@bot.message_handler(commands=['note_count'])
def note_count(message):
    count = count_note(message.from_user.id)
    text = plural_ru(count, ('запись', 'записи', 'записей'))
    bot.send_message(message.chat.id, f"Ты записал {count} {text}")
    
def plural_ru(count, forms):
    if count % 10 == 1 and count % 100 != 11:
        return forms[0]
    elif 2 <= count % 10 <= 4 and not (12 <= count % 100 <= 14):
        return forms[1]
    else:
        return forms[2]

# функция для просмотра вашей активности с этим ботом
@bot.message_handler(commands=['activity'])
def check_activity(message):
    bot.send_message(message.chat.id,activity_note(message.from_user.id) )


if __name__ == "__main__":
 setup_bot_commands()
 bot.infinity_polling(skip_pending=True)
