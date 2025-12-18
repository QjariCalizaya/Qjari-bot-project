import logging
import random

import telebot
from telebot import types
from config import MAX_PROMPT_CHARS_DEFAULT ,SHOW_MODEL_FOOTER_DEFAULT, DEBUG_SETTINGS_SHOW, CMD_MODEL_ID_ENABLED
from db import *
from db import (get_character_by_id)
from metrics import metric
from logging_config import setup_logging
from openrouter_client import *
from db import (get_bool_setting, write_error_call, write_error_log, is_feature_enabled, set_settings, set_feature_toggle)
from metrics import metric, timed
from typing import Iterable



load_dotenv()
TOKEN = os.getenv("TOKEN") or ""
init_db() 
setup_logging()
log = logging.getLogger(__name__)
log.info("Старт приложения (инициализация бота)")

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
    if is_feature_enabled("debug_settings", DEBUG_SETTINGS_SHOW):
        commands.append(types.BotCommand("debug_settings", "Показать настройки бота"))

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
    log.debug("запущена команад /start")
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
    log.debug(f"команда start вернула текст: \n{text}")
    bot.reply_to(message,text)

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

    if not is_feature_enabled("model_commands",CMD_MODEL_ID_ENABLED):
        bot.reply_to(message, "команды выбора модели временно отключены")
        return

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



@bot.message_handler(commands=["ask"])
def cmd_ask(message: types.Message) -> None:
    """
    Задать вопрос LLM модели
    """
    metric.counter("commands_total").inc()
    metric.counter("ask_requests_total").inc()

    user_id = message.from_user.id
    q = message.text.replace("/ask", "", 1).strip()
    if not q:
        bot.reply_to(message, "Использование: /ask <вопрос>")
        return

    max_len = get_int_setting("max_prompt_chars",MAX_PROMPT_CHARS_DEFAULT)
    msgs = _build_messages(user_id, q[:max_len])
    model_key = get_active_model()["key"]

    log.info("Команда /ask от user_id=%s, вопрос=%.80s", user_id, q)

    try:
        text, ms = chat_once(msgs, model=model_key, temperature=0.2, max_tokens=400)

    except OpenRouterError as e:
        metric.counter("openrouter_errors_total").inc()

        log.error("OpenRouterError при /ask от user_id=%s: %s", user_id, e)
        write_error_log(
            level="ERROR",
            logger_name=__name__,
            message=str(e),
            user_id=user_id,
            command="/ask",
            details=None,
        )
        bot.reply_to(message, f"Ошибка: {e}")
        return
    except Exception:
        log.exception("Непредвиденная ошибка при /ask от user_id=%s", user_id)
        write_error_log(
            level="ERROR",
            logger_name=__name__,
            message=f"Unhandled error in /ask: {e}",
            user_id=user_id,
            command="/ask",
            details=None,
        )
        bot.reply_to(message, "Непредвиденная ошибка.")
        return

    metric.latency("openrouter_latency_ms").observe(ms)

    out = (text or "").strip()[:4000]  # не переполняем сообщение Telegram
    
    show_footer = get_bool_setting("show_model_footer", SHOW_MODEL_FOOTER_DEFAULT)
    add_info = f"\n\n({ms} MC: модель: {model_key})" if show_footer else ""
    
    bot.reply_to(message, f"{out}{add_info}")

    

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

@bot.message_handler(commands=['stats'])
def handle_stats(message: types.Message)->None:
    user_id = message.from_user.id
    metric.counter("commands_total").inc()
    log.info("команда /stats от user_id=%s", user_id)
    stats = metric.snapshot()
    counters = stats["counters"]
    latencies = stats["latencies"]
    lines: list[str] = []
    lines.append("статистика бота\n")
    lines.append("Счетчики:")
    if counters:
        for name, value in sorted(counters.items()):
            lines.append(f"{name}: {value}")
    else:
        lines.append("-нет данных")

    lines.append("\nЗамены времени")
    if latencies:
        for name, data in sorted(latencies.items()):
            lines.append(
                f" {name}: count = {data['count']},"
                f"avg = {data['avg']},0f"
                f"max = {data['max']},"
                f"min = {data['min']}"
            )
    else:
        lines.append("no data")
    bot.reply_to(message, "\n".join(lines))


@bot.message_handler(commands=["debug_settings"])
def cmd_debug_settings(message):
    max_len = get_int_setting("max_prompt_chars", MAX_PROMPT_CHARS_DEFAULT)
    show_footer = get_bool_setting("show_model_footer", SHOW_MODEL_FOOTER_DEFAULT)
    model_cmd = is_feature_enabled("model_commands", CMD_MODEL_ID_ENABLED)

    text = (
        f"max_prompt_chars = {max_len}\n"
        f"show_model_footer = {show_footer}\n"
        f"feature: model_commands = {model_cmd}\n"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['set_settings'])
def cmd_set_settings(message:types.Message)-> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or "=" not in parts[1]:
        bot.reply_to(message, "использование: /set_settings ключ=значение")
        return
    key , value = parts[1].split("=", 1)
    key = key.strip()
    value.value.strip()

    if not key:
        bot.reply_to(message, "ключ параметра неможет быть пустым")
        return
    set_settings(key, value)
    bot.reply_to(message, f"параметр {key} установлен в {value}")


@bot.message_handler(commands=['set_toggle'])
def cmd_set_toggle(message: types.Message)->None:
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "использование: /set_toggle имя on|off")
        return
    name = parts[1].strip()
    state = parts[2].strip().lower()
    if state not in ("on","off"):
        bot.reply_to(message, "Второй аргумент должен быть on или off")
        return
    enabled = state == "on"
    set_feature_toggle(name,enabled)
    bot.reply_to(message, f"Feature-toggle {name} = {enabled}")

if __name__ == "__main__":
    setup_bot_commands()
    bot.infinity_polling(skip_pending=True)