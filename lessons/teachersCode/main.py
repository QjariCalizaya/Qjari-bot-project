import random
from typing import List, Literal

import requests
import telebot

from config import config, logger
from db import add_note, count_notes, delete_note, find_note, init_db, list_notes, set_user_character, update_note
from db import get_active_model, get_model_by_id, list_models, set_active_models
from db import get_character_by_id, get_user_character, list_characters
from openrouter_client import chat_once, OpenRouterError

NOTE_MESSAGE_PATTERN = '''Заметка: {{note}}\nСоздана: {{created_at}}'''

bot = telebot.TeleBot(config.token)


def _setup_bot_commands(bot: telebot.TeleBot):
    bot.set_my_commands(
        [
            telebot.types.BotCommand(command='start', description='Start bot'),
            telebot.types.BotCommand(command='help', description='Help message'),
            telebot.types.BotCommand(command='about', description='About the bot'),
            telebot.types.BotCommand(command='sum', description='Summation of digits'),
            telebot.types.BotCommand(command='confirm', description='Confirm action'),
            telebot.types.BotCommand(command='weather', description='Get weather'),
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
            telebot.types.BotCommand(command='whoami', description='Get active model and active character')
        ]
    )
    logger.info('Bot commands loaded.')


def _fetch_weather_moscow_open_meteo() -> str:
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": 55.7558,
        "longitude": 37.6173,
        "current": "temperature_2m",
        "timezone": "Europe/Moscow"
    }

    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        t = r.json()["current"]["temperature_2m"]

        return f"Москва: сейчас {round(t)}°C"

    except Exception:
        return "Не удалось получить погоду."


def _parse_number(text: str) -> list[int]:
    tokens = text.strip().replace(',', ' ').split()
    numbers = []

    for token in tokens:
        if token.replace('.', '').lstrip('-').isdigit():
            numbers.append(int(token))

    logger.debug(f'Parsing numbers: {text}. Tokens: {tokens} Result: {numbers}')

    return numbers


def _sum_process(text: str) -> str:
    numbers = _parse_number(text)

    if not numbers:
        result = 'В сообщении нет цифр.\nПример использования команды: /sum 2 3 10'
    else:
        result = f'Сумма: {sum(numbers)}'

    logger.debug(f'Summation of numbers: {text}. Result: {result}')

    return result


def _max_process(text: str) -> str:
    numbers = _parse_number(text)

    if not numbers:
        result = 'В сообщении нет цифр.\nПример использования команды: /max 1 3 7'
    else:
        result = f'Максимум: {max(numbers)}'

    logger.debug(f'Maximum numbers: {text}. Result: {result}')

    return result


def _create_keyboard() -> telebot.types.ReplyKeyboardMarkup:
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row('Погода', 'Сумма')
    keyboard.row('О боте', 'Помощь')
    keyboard.row('Скрыть клавиатуру')

    return keyboard


def _create_note_keyboard(
        cmd_type: Literal['list', 'find'],
        count: int,
        offset: int,
        step: int = 10,
        text: str = 'none'
) -> telebot.types.InlineKeyboardMarkup:
    keyboard = telebot.types.InlineKeyboardMarkup()

    if offset == 0:
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                text='След. Стр.',
                callback_data=f'note:{cmd_type}:{count}:{offset + step}:{step}:{text}')
        )

    elif count - offset > step:
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                text='Пред. Стр.',
                callback_data=f'note:{cmd_type}:{count}:{offset - step}:{step}:{text}'
            ),
            telebot.types.InlineKeyboardButton(
                text='След. Стр.',
                callback_data=f'note:{cmd_type}:{count}:{offset + step}:{step}:{text}'
            )
        )

    else:
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                text='Пред. Стр.',
                callback_data=f'note:{cmd_type}:{count}:{offset - step}:{step}:{text}'
            )
        )

    return keyboard


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


@bot.message_handler(commands=['start'])
def send_start(message: telebot.types.Message):
    bot.reply_to(message, 'Привет! Я простой бот! Напиши /help', reply_markup=_create_keyboard())
    logger.info(f'Sent start message for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['help'])
def send_help(message: telebot.types.Message):
    bot.reply_to(message, '/start - Начать\n/help - Помощь\n/about - О боте\n/sum - Суммирование чисел\n/confirm - Подтвердить действие\n/weather - Погода')
    logger.info(f'Sent help message for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['about'])
def send_about(message: telebot.types.Message):
    bot.reply_to(message, 'Простой телеграм бот в рамках семинарских занятий.\nАвтор: Агаев Арсений Валерьевич 1032221668')
    logger.info(f'Sent about message for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['sum'])
def send_sum(message: telebot.types.Message):
    text = _sum_process(message.text.replace('/sum', ''))

    bot.reply_to(message, text)
    logger.info(f'Sent sum message for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['max'])
def send_max(message: telebot.types.Message):
    text = _max_process(message.text.replace('/max', ''))

    bot.reply_to(message, text)
    logger.info(f'Sent max message for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['hide'])
def hide_keyboard(message: telebot.types.Message):
    bot.send_message(message.chat.id, 'Клавиатура спрятана', reply_markup=telebot.types.ReplyKeyboardRemove())
    logger.info(f'Keyboard remove for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['show'])
def show_keyboard(message: telebot.types.Message):
    bot.send_message(message.chat.id, 'Клавиатура активна', reply_markup=_create_keyboard())
    logger.info(f'Keyboard show for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['confirm'])
def send_confirm(message: telebot.types.Message):
    keyboard = telebot.types.InlineKeyboardMarkup()

    keyboard.add(
        telebot.types.InlineKeyboardButton('Да', callback_data='confirm:yes'),
        telebot.types.InlineKeyboardButton('Нет', callback_data='confirm:no')
    )

    bot.send_message(message.chat.id, 'Подтвердить действие?', reply_markup=keyboard)
    logger.info(f'Sent confirm message for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['weather'])
def send_weather(message: telebot.types.Message):
    weather = _fetch_weather_moscow_open_meteo()

    bot.reply_to(message, weather)
    logger.info(f'Sent weather message for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['add_note'])
def send_add_note(message: telebot.types.Message):
    note = message.text.replace('/add_note', '')

    if note:
        note_id = add_note(message.from_user.id, note)
        text = f'Заметка "{note}" ({note_id}) успешно добавлена.'

    else:
        text = 'В сообщении нет текста заметки.\nПример добавления заметки: /add_note Новая заметка'

    bot.reply_to(message, text)
    logger.info(f'Sent add note message for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['list_notes'])
def send_list_notes(message: telebot.types.Message):
    count = count_notes(message.from_user.id)
    reply_markup = None

    if count > 0:
        notes = list_notes(message.from_user.id)
        notes_message_text = [
            NOTE_MESSAGE_PATTERN.replace('{{note}}', note[1]).replace('{{created_at}}', note[2])
            for note in notes
        ]
        text = '\n\n'.join(notes_message_text)

        if count > 10:
            reply_markup = _create_note_keyboard('list', count, 0)

    else:
        text = 'Список заметок пуст'

    bot.reply_to(message, text, reply_markup=reply_markup)
    logger.info(f'Sent list notes for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['find_note'])
def send_find_note(message: telebot.types.Message):
    message_text = message.text.replace('/find_note', '').strip()
    reply_markup = None

    if message_text:
        notes = find_note(message.from_user.id, message_text)
        count = count_notes(message.from_user.id, message_text)

        if count > 0:
            notes_message_text = [
                NOTE_MESSAGE_PATTERN.replace('{{note}}', note[1]).replace('{{created_at}}', note[2])
                for note in notes
            ]
            text ='\n\n'.join(notes_message_text)

            if count > 10:
                reply_markup = _create_note_keyboard('find', count, 0, text=message_text)

        else:
            text = 'Ничего не найдено'

    else:
        text = 'В сообщении нет искомого текста.\nПример поиска заметки: /find_note Какой-то текст'

    bot.reply_to(message, text, reply_markup=reply_markup)
    logger.info(f'Sent find note message for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['edit_note'])
def send_edit_note(message: telebot.types.Message):
    tokens = message.text.replace('/edit_note', '').strip().split(maxsplit=1)

    if tokens:
        if len(tokens) == 2:
            note_id, note_text = tokens

            if note_id.isdigit():
                note_id = int(note_id)

                if update_note(message.from_user.id, int(note_id), note_text):
                    text = f'Заметка "{note_id}" успешно изменена.'

                else:
                    text = f'Ошибка при обновлении заметки "{note_id}".'
                    logger.error(f'Error updating note id {note_id} (Message: {message.text}).')

            else:
                text = 'Номер заметки должен быть числом.\nПример обновления заметки: /edit_note 1 Новый текст заметки'

        else:
            text = 'Неправильный формат команды.\nПример обновления заметки: /edit_note 1 Новый текст заметки'

    else:
        text = 'В сообщении нет номера и текста заметки.\nПример добавления заметки: /edit_note Новая заметка'

    bot.reply_to(message, text)
    logger.info(f'Sent edit note message for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['delete_note'])
def send_delete_note(message: telebot.types.Message):
    note_id = message.text.replace('/delete_note', '').strip()

    if note_id.isdigit():
        note_id = int(note_id)

        if delete_note(message.from_user.id, note_id):
            text = f'Заметка "{note_id}" успешно удалена.'

        else:
            text = f'Ошибка при удалении заметки "{note_id}".'
            logger.error(f'Error deleting note id {note_id} (Message: {message.text}).')

    else:
        text = 'Номер заметки должен быть числом.\nПример удаления заметки: /delete_note 1'

    bot.reply_to(message, text)
    logger.info(f'Sent delete note message for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['count_notes'])
def send_count_notes(message: telebot.types.Message):
    count = count_notes(message.from_user.id)

    bot.reply_to(message, f'Сохранено заметок: {count}')
    logger.info(f'Sent count notes for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['models'])
def send_cmd_models(message: telebot.types.Message):
    items = list_models()

    if items:
        lines = ['Доступные модели:']

        for model in items:
            star = '*' if model['active'] else ''
            lines.append(f'{star} {model["id"]}. {model["label"]} {model["key"]}')

        lines.append('\nДля активации введите /model <ID>')
        text = '\n'.join(lines)

    else:
        text = 'Список моделей пуст'

    bot.reply_to(message, text)
    logger.info(f'Sent models for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['model'])
def send_cmd_model(message: telebot.types.Message):
    token = message.text.replace('/model', '').strip()

    if not token:
        active_model = get_active_model()
        text = f'Текущая активная модель: {active_model["label"]} {active_model["key"]}\n Для смены модели введите /model <ID>'

    elif not token.isdigit():
        text = f'ID модели должен быть числом.\nПример активации модели: /model 1'

    else:
        active_model = set_active_models(int(token))
        text = f'Активная модель переключена: {active_model["label"]} {active_model["key"]}'

    bot.reply_to(message, text)
    logger.info(f'Sent model for {message.from_user.id} ({message.from_user.first_name}).')


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
            text = f'Ошибка: {e}'

        except Exception as e:
            text = 'Непредвиденная ошибка'
            logger.error(e)

    bot.reply_to(message, text)
    logger.info(f'Sent ask for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['ask_model'])
def send_cmd_ask_model(message: telebot.types.Message):
    tokens = message.text.replace('/ask_model', '').strip().split(maxsplit=1)
    model_key = None

    if not tokens:
        text = 'Отсутствуют аргументы. Пример использования:\n/ask_model <ID> Вопрос'

    elif len(tokens) != 2:
        text = 'Отсутствуют аргументы или их слишком много. Пример использования:\n/ask_model <ID> Вопрос'

    elif not tokens[0].isdigit():
        text = 'ID не является числом. Пример использования:\n /ask_model 1 Вопрос'

    else:
        try:
            llm_message = _build_messages(message.from_user.id, tokens[1][:600])
            model_key = get_model_by_id(int(tokens[0]))['key']

            try:
                text, ms = chat_once(llm_message, model=model_key, temperature=0.2, max_tokens=400)
                text = text.strip()[:4096]

            except OpenRouterError as e:
                text = f'Ошибка: {e}'

            except Exception as e:
                text = 'Непредвиденная ошибка'
                logger.error(e)

        except ValueError:
            text = 'Неизвестный ID модели. Используйте /models для получения списка моделей'

    bot.reply_to(message, text)
    logger.info(f'Sent ask {model_key} for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['ask_random'])
def send_cmd_ask_random(message: telebot.types.Message):
    token = message.text.replace('/ask_random', '').strip()
    characters = list_characters()

    if not token:
        text = 'Отсутствует текст вопроса. Пример использования:\n /ask Вопрос'

    elif not characters:
        text = 'Каталог персонажей пуст'

    else:
        chosen = random.choice(characters)
        character = get_character_by_id(chosen['id'])

        llm_message = _build_messages(message.from_user.id, token, character)
        model_key = get_active_model()['key']

        try:
            text, ms = chat_once(llm_message, model=model_key, temperature=0.2, max_tokens=400)
            text = text.strip()[:4096]

        except OpenRouterError as e:
            text = f'Ошибка: {e}'

        except Exception as e:
            text = 'Непредвиденная ошибка'
            logger.error(e)

    bot.reply_to(message, text)
    logger.info(f'Sent random ask for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['characters'])
def send_cmd_characters(message: telebot.types.Message):
    characters = list_characters()

    if not characters:
        text = 'Каталог персонажей пуст.'

    else:
        try:
            current_character = get_user_character(message.from_user.id)['id']

        except Exception:
            current_character = None

        lines = ['Доступные персонажи:']

        for character in characters:
            star = '*' if current_character is not None and character['id'] == current_character else ' '
            lines.append(f'{star} {character["id"]}. {character["name"]}')

        lines.append('Для выбора используйте /character <ID>')
        text = '\n'.join(lines)

    bot.reply_to(message, text)
    logger.info(f'Sent characters for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['character'])
def send_cmd_character(message: telebot.types.Message):
    token = message.text.replace('/character', '').strip()

    if not token:
        character = get_user_character(message.from_user.id)
        text = f'Текущий персонаж: {character["name"]}\n Чтобы сменить используйте /character <ID>'

    elif not token.isdigit():
        text = 'ID не является числом. Пример использования:\n /character 1'

    else:
        try:
            character = set_user_character(message.from_user.id, int(token))
            text = f'Персонаж установлен: {character["name"]}'

        except ValueError:
            text = 'Неизвестный ID персонажа. Используйте /characters для получения списка персонажей'

    bot.reply_to(message, text)
    logger.info(f'Sent character for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(commands=['whoami'])
def send_cmd_whoami(message: telebot.types.Message):
    character = get_user_character(message.from_user.id)
    model = get_active_model()

    bot.reply_to(message,f'Модель: {model["label"]} [{model["key"]}]\nПерсонаж: {character["name"]}')
    logger.info(f'Sent whoami for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(func=lambda message: message.text == 'Помощь')
def send_help_button(message: telebot.types.Message):
    send_help(message)
    logger.info(f'Process keyboard button "Помощь" for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(func=lambda message: message.text == 'О боте')
def send_about_button(message: telebot.types.Message):
    send_about(message)
    logger.info(f'Process keyboard button "О боте" for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(func=lambda message: message.text == 'Сумма')
def send_sum_button(message: telebot.types.Message):
    bot.send_message(message.chat.id, 'Введите числа через пробел или запятую:')
    bot.register_next_step_handler(message, send_text_sum)
    logger.info(f'Process keyboard button "Сумма" for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(func=lambda message: message.text == 'Скрыть клавиатуру')
def hide_keyboard_button(message: telebot.types.Message):
    hide_keyboard(message)
    logger.info(f'Process keyboard button "Скрыть клавиатуру" for {message.from_user.id} ({message.from_user.first_name}).')


@bot.message_handler(func=lambda message: message.text == 'Погода')
def send_weather_button(message: telebot.types.Message):
    send_weather(message)
    logger.info(f'Process keyboard button "Погода" for {message.from_user.id} ({message.from_user.first_name}).')


def send_text_sum(message: telebot.types.Message):
    text = _sum_process(message.text)

    bot.reply_to(message, text)
    logger.info(f'Summarization from text for {message.from_user.id} ({message.from_user.first_name}).')


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm:'))
def send_confirm_yes_button(call: telebot.types.CallbackQuery):
    choice = call.data.split(':', 1)[1]

    bot.answer_callback_query(call.id, 'Принято')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    bot.send_message(call.message.chat.id, 'Готово!' if choice == 'yes' else 'Отменено.')
    logger.info(f'Process inline keyboard button "{call.data}" for {call.message.chat.id}.')


@bot.callback_query_handler(func=lambda call: call.data.startswith('note:'))
def send_notes(call: telebot.types.CallbackQuery):
    # note:{cmd_type}:{count}:{offset}:{step}:{text}
    _, cmd_type, count, offset, step, find_text = call.data.split(':')

    if cmd_type == 'list':
        notes = list_notes(call.from_user.id, int(step), int(offset))

    elif cmd_type == 'find':
        notes = find_note(call.from_user.id, find_text, int(step), int(offset))

    else:
        return

    notes_message_text = [
        NOTE_MESSAGE_PATTERN.replace('{{note}}', note[1]).replace('{{created_at}}', note[2])
        for note in notes
    ]
    text = '\n\n'.join(notes_message_text)
    reply_markup = _create_note_keyboard(cmd_type, int(count), int(offset), int(step), find_text)

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=reply_markup)
    logger.info(f'Process inline keyboard button "{call.data}" for {call.message.chat.id}.')


if __name__ == '__main__':
    init_db()

    _setup_bot_commands(bot)

    logger.info('Telegram Bot started.')
    bot.infinity_polling(skip_pending=True)