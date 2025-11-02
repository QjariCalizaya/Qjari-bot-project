import os
import telebot
from telebot import types
from dotenv import load_dotenv
from typing import List, Literal
import logging
from db import *
import random
from db import (get_character_by_id)
from openrouter_client import *
from config import logger

load_dotenv()
TOKEN = os.getenv("TOKEN") or ""

init_db() 

if not TOKEN:
    raise RuntimeError("there isn't TOKEN in .env")

bot = telebot.TeleBot(TOKEN)


def setup_bot_commands():
    commands = [
            telebot.types.BotCommand(command='start', description='Start bot'),
            telebot.types.BotCommand(command='help', description='Help message'),
            telebot.types.BotCommand(command='about', description='About the bot'),
            #telebot.types.BotCommand(command='sum', description='Summation of digits'),
            telebot.types.BotCommand(command='confirm', description='Confirm action'),
            #telebot.types.BotCommand(command='weather', description='Get weather'),
            telebot.types.BotCommand(command='add_note', description='Add note'),
            telebot.types.BotCommand(command='list_notes', description='List of note'),
            telebot.types.BotCommand(command='find_note', description='Search note'),
            telebot.types.BotCommand(command='edit_note', description='Edit note'),
            telebot.types.BotCommand(command='delete_note', description='Delete note'),
            telebot.types.BotCommand(command='count_notes', description='Count of note'),
            telebot.types.BotCommand(command='model', description='Set active model'),
            telebot.types.BotCommand(command='models', description='Get list of AI models'),
            telebot.types.BotCommand(command='ask', description='Ask the model a question'),
            telebot.types.BotCommand(command='ask_model', description='Ask a question a specific model'),
            telebot.types.BotCommand(command='ask_random', description='Ask the random character'),
            telebot.types.BotCommand(command='characters', description='Get list of characters'),
            telebot.types.BotCommand(command='character', description='Get active character or set new character'),
            telebot.types.BotCommand(command='character_name', description='Change character name'),
            telebot.types.BotCommand(command='whoami', description='Get active model and active character')


    ]

    bot.set_my_commands(commands)

""" 
@bot.message_handler(commands=['start' , 'help'])
def start_help(message):
    welcome_text = "Привет!!, я учебный бот который сохраняет список"
    bot.reply_to(message,welcome_text) """

@bot.message_handler(commands=['start','help'])
def cmd_start(message: types.Message)-> None:
    """
    
    """
    text = (
        "привет! это заметочник на SQLite. \n\n"
        "команда: \n"
        "/note_add <текст>\n"
        "/note_list [N]\n"
        "/note_find <подстрока>\n"
        "/note_edit <id> <текст>\n"
        "/note_del <id>\n"
        "/note_count\n"
        "/note_export\n"
        "note_stats [days]\n"
        "/models\n"
        "/model <id>\n"
    )

@bot.message_handler(commands=['note_add'])
def note_add(message):
    bot.send_message(message.chat.id, "Введи текст заметки")
    bot.register_next_step_handler(message, save_note)


def save_note(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if not text:
        bot.reply_to(message, "Текст пустой, попробуй снова.")
        return

    note_id = add_note(user_id, text)   # usar tu función
    bot.reply_to(message, f"Заметка сохранена (id={note_id})" )

@bot.message_handler(commands=['note_list'])
def note_list(message):
    note = list_notes(message.from_user.id)
    text = ""
    for note_id, note_text, created_at in note:
        text += f"\n[{note_id}] {note_text} ({created_at})"

    bot.send_message(message.chat.id, text )

@bot.message_handler(commands=['note_find'])
def note_find(message):
    bot.send_message(message.chat.id, "введи текст для потиска")
    bot.register_next_step_handler(message,find )

def find(message):
    note = find_notes(message.from_user.id , message.text)
    text = ""
    for note_id, note_text, created_at in note:
        text += f"\n[{note_id}] {note_text} ({created_at})"

    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['note_edit'])
def note_edit(message):
    bot.send_message(message.chat.id, "Введи ID заметки, которую хочешь изменить")
    bot.register_next_step_handler(message, edit_step)


def edit_step(message):
    user_id = message.from_user.id
    try:
        note_id = int(message.text.strip())
    except ValueError:
        bot.reply_to(message, "ID должен быть числом")
        return
    
    bot.send_message(message.chat.id, "Введи новый текст")
    # aquí pasamos note_id como argumento extra
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



@bot.message_handler(commands=["models"])
def cmd_models(message: types.Message) -> None:
    items = list_models()
    if not items:
        bot.reply_to(message, "Список моделей пуст.")
        return
    lines = ["Доступные модели:"]
    for m in items:
        star = "★" if m["active"] else " "
        lines.append(f"{star} {m['id']}. {m['label']}  [{m['key']}]")
    lines.append("\nАктивировать: /model <ID>")
    bot.reply_to(message, "\n".join(lines))


@bot.message_handler(commands=['model'])
def cmd_model(message: types.Message)->None:
    arg = message.text.replace("/model" , "" , 1).strip()
    if not arg:
        active = get_active_model()
        bot.reply_to(message , f"Текущая активная моедль: {active['label']} [{active['key']}]\n(сменить: /model <ID> или /models)")
        return
    if not arg.isdigit():
        bot.reply_to(message, "Использование: /model <ID из /models>")
        return
    try:
        active = set_active_model(int(arg))
        bot.reply_to(message, f"Активная модель переключена: {active['label']} [{active["key"]}]")
    except ValueError:
        bot.reply_to(message, "Неизвестный ID модели. Сначала /models.")

@bot.message_handler(commands=['ask'])
def send_cmd_ask(message: telebot.types.Message):
    token = message.text.replace('/ask', '').strip()

    if not token:
        text = 'Отсутствует текст вопроса. Пример использования:\n /ask Вопрос'

    else:
        llm_message = _build_messages(message.from_user.id, token[:600])
        model_key = get_active_model()['key']

        try:
            text, ms = chat_once(llm_message, model=model_key, temperature=0.2, max_tokens=400)
            text = text.strip()[:4096]

        except OpenRouterError as e: 
            text = f'Ошибка test: {e}'

        except Exception as e:
            text = 'Непредвиденная ошибка'
            logger.error(e)

    bot.reply_to(message, text)


@bot.message_handler(commands=['characters'])
def cmd_characters(message: types.Message)->None:
    user_id = message.from_user.id
    items = list_characters()
    if not items:
        bot.reply_to(message, "Каталог песонажей пуст")
        return
    try:
        current = get_user_character(user_id)["id"]
    except Exception:
        current = None
    lines = ['доступные персонажи:']
    for p in items:
        star = "*" if current is not None and p["id"] == current else " "
        lines.append(f"{star} {p['id']}. {p['name']}" )
    lines.append("\nвыбор: /character <ID>")
    bot.reply_to(message, "\n".join(lines))


@bot.message_handler(commands=["character"])
def cmd_character(message: types.Message)-> None:
    user_id = message.from_user.id
    arg = message.text.replace("/character", "", 1).strip()
    if not arg:
        p = get_user_character(user_id)
        bot.reply_to(message, f"текущий персонаж: {p['name']}\n(сменить: /character, затем /character <ID>)")
        return
    if not arg.isdigit():
        bot.reply_to(message, "Испльзование: /character <ID из /characters>")
        return
    try:
        p = set_user_character(user_id, int(arg))
        bot.reply_to(message, f"Персонаж установлен: {p['name']}")
    except ValueError:
        bot.reply_to(message, "Неисвестный ID персонажа. Сначала /characters.")


@bot.message_handler(commands=['whoami'])
def send_cmd_whoami(message: telebot.types.Message):
    character = get_user_character(message.from_user.id)
    model = get_active_model()

    bot.reply_to(message,f'Модель: {model["label"]} [{model["key"]}]\nПерсонаж: {character["name"]}')
    #logger.info(f'Sent whoami for {message.from_user.id} ({message.from_user.first_name}).')

def _build_messages(user_id: int, text: str, character: dict | None = None) -> List[dict[str, str]]:
    if character  is None:
        character = get_user_character(user_id)

    system = (
        f'Ты отвечаешь строго в образе персонажа: {character["name"]}.\n'
        f'{character["prompt"]}\n'
        'Правила:\n'
        '1. Всегда держи стиль и манеру речи выбранного персонажа. При необходимости - переформулируй.\n'
        '2. Технические ответы давай корректно и по пунктам, но в характерной манере.\n'
        '3. Не раскрывай, что ты "играешь роль".\n'
        '4. Не используй длинные дословные цитаты из фильмов/книг (>10 слов).\n'
        'Если стиль персонажа выражен слабо - переформулируй ответ и усиль характер персонажа, сохраняя фактическую точность.\n'
    )

    return [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': text}
    ]

def _build_message_for_character(character: dict, user_text: str)->list[dict]:
    system = (

        f"Ты отвечаешь строго в образе персонажа: {character['name']}.\n"
        f"{character['prompt']}\n"
        "Правила:\n"
        "1)Всегда держи стиль и нанеру речи выбранного персонажа. при необходимости - переформулируй\n"
        "2) Технические ответы давай корекно и по пунктам, но в характерной манере.\n"
        "3)не раскрывай, что ты 'играешь роль'.\n"
        "4)не используй длинные дословные цитаты из фильмов/книг(>10 слов).\n"
        "5)Если стиль персонажа выражен слабо - переформулируй ответ и усили характер персонажа, сохраняя фактическую точность\n"
    )
    return [
        {"role": "system" , "content": system},
        {"role": "user", "content": user_text}
    ]


@bot.message_handler(commands=['ask_random'])
def cmd_ask_random(message: types.Message)->None:
    q = message.text.replace("/ask_random", "", 1).strip()
    if not q:
        bot.reply_to(message, "Использование: /ask_random<вопрос>")
        return
    q = q[:600]
    items = list_characters()
    if not items:
        bot.reply_to(message, "каталог персонажей пуст.")
        return
    chosen = random.choice(items)
    character = get_character_by_id(chosen["id"])

    msgs = _build_message_for_character(character, q)
    model_key = get_active_model()["key"]
    try:
        text , ms = chat_once(msgs, model=model_key, temperature=0.2 , max_tokens=400)
        out = (text or "").strip()[:4000]
        bot.reply_to(message, f"{out}\n\n({ms} MC; модель: {model_key}; как: {character['name']})")
    except OpenRouterError as e:
        bot.reply_to(message, f"ошибка: {e}")
    except Exception:
        bot.reply_to(message, "Непредвиденная ошибка")

@bot.message_handler(commands=['ask_model'])
def cmd_ask_model(message: types.Message)->None:
    q = message.text.replace("/ask_model","",1).strip()
    if not q:
        bot.reply_to(message, "Использование: /ask_model <ID> <вопрос>")
        return
    q = q[:600]
    
    items = list_characters()
    if not items:
        bot.reply_to(message, "каталог персонажей пуст.")
        return
    parts = q.split(maxsplit=1)  # separa ID de la pregunta
    if len(parts) < 2:
        bot.reply_to(message, "Использование: /ask_model <ID> <вопрос>")
        return

    id_str, question = parts
    try:
        id = int(id_str)
    except ValueError:
        bot.reply_to(message, "ID должен быть числом")
        return
    
    character = get_character_by_id(id)
    if not character:
        bot.reply_to(message, "указан неправильный ID (список character /characters)")
        return
    msgs = _build_message_for_character(character,question)
    model_key = get_model_key_by_ID(id)["key"]

    try:
        text , ms = chat_once(msgs,model=model_key, temperature=0.2, max_tokens=400)
        out = (text or "").strip()[:4000]
        bot.reply_to(message , f"{out}\n\n({ms} MC; модель: {model_key}; как: {character['name']})" )
    except OpenRouterError as e:
        bot.reply_to(message, f"ошибка: {e}")
    except Exception:
        bot.reply_to(message, "Непредвиденная ошибка")

if __name__ == "__main__":
    setup_bot_commands()
    bot.infinity_polling(skip_pending=True)