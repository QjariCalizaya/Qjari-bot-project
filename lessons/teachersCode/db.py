import sqlite3

import telebot

from config import config, logger


def _connect():
    conn = sqlite3.connect(config.db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA busy_timeout = 5000')

    return conn


def create_notes_table():
    schema = '''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        '''

    with _connect() as conn:
        conn.executescript(schema)


def add_note(user_id: int, text: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            'INSERT INTO notes(user_id, text) VALUES (?, ?)',
            (user_id, text)
        )

        return cur.lastrowid


def list_notes(user_id: int, limit: int = 10, offset: int = 0) -> list:
    with _connect() as conn:
        cur = conn.execute(
            '''SELECT id, text, created_at
            FROM notes
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            OFFSET ?''',
            (user_id, limit, offset)
        )

        return cur.fetchall()


def find_note(user_id: int, text: str, limit: int = 10, offset: int = 0) -> list:
    with _connect() as conn:
        cur = conn.execute(
            '''SELECT id, text, created_at
            FROM notes
            WHERE user_id = ?
            AND text like '%' || ? || '%' COLLATE NOCASE
            ORDER BY id DESC
            LIMIT ?
            OFFSET ?''',
            (user_id, text, limit, offset)
        )

        return cur.fetchall()


def update_note(user_id: int, note_id: int, text: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            '''UPDATE notes
            SET text = ?
            WHERE user_id = ?
            AND id = ?''',
            (text, user_id, note_id)
        )

        return cur.rowcount > 0


def delete_note(user_id: int, note_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            '''DELETE FROM notes
            WHERE user_id = ?
            AND id = ?''',
            (user_id, note_id)
        )

        return cur.rowcount > 0


def count_notes(user_id: int, text = '') -> int:
    with _connect() as conn:
        cur = conn.execute(
            '''SELECT COUNT(*)
            FROM notes
            WHERE user_id = ?
            AND text like '%' || ? || '%' COLLATE NOCASE''',
            (user_id, text)
        )

        return cur.fetchone()[0]


def create_models_table():
    schema = '''
    CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY,
        key TEXT NOT NULL UNIQUE,
        label TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0, 1))
    );
    
    CREATE UNIQUE INDEX IF NOT EXISTS ux_models_single_active
    ON models(active) WHERE active=1;
    '''

    with _connect() as conn:
        conn.executescript(schema)


def list_models() -> list[dict[str, str | bool]]:
    with _connect() as conn:
        cur = conn.execute(
            '''SELECT id, key, label, active
            FROM models
            ORDER BY id'''
        )
        rows = cur.fetchall()
        result = [
            {
                'id': row['id'],
                'key': row['key'],
                'label': row['label'],
                'active': bool(row['active'])
            }
            for row in rows
        ]

        return result


def get_active_model() -> dict[str, str | bool]:
    with _connect() as conn:
        result = {}

        cur = conn.execute(
            '''SELECT id, key, label
            FROM models
            WHERE active=1'''
        )
        row = cur.fetchone()

        if not row:
            cur = conn.execute(
                '''SELECT id, key, label
                FROM models
                ORDER BY id
                LIMIT 1'''
            )
            row = cur.fetchone()

        if not row:
            raise RuntimeError('В реестре моделей нет записей.')

        conn.execute(
            '''UPDATE models
            SET active = CASE WHEN id=?
            THEN 1 ELSE 0 END''',
            (row['id'],)
        )

        result.update({
            'id': row['id'],
            'key': row['key'],
            'label': row['label'],
            'active': True
        })

        return result


def get_model_by_id(id: int) -> dict[str, str | bool]:
    with _connect() as conn:
        cur = conn.execute(
            '''SELECT id, key, label
            FROM models
            WHERE id=?''',
            (id,)
        )
        row = cur.fetchone()

        if not row:
            raise ValueError('Неизвестный ID модели.')

        return {
            'id': row['id'],
            'key': row['key'],
            'label': row['label']
        }


def set_active_models(model_id: int) -> dict[str, str | bool]:
    with _connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        exits = conn.execute(
            '''SELECT 1
            FROM models
            WHERE id=?''',
            (model_id,)
        ).fetchone()

        if not exits:
            conn.rollback()
            raise ValueError('Неизвестный ID модели')

        conn.execute(
            '''UPDATE models
            SET active = CASE WHEN id=?
            THEN 1 ELSE 0 END''',
            (model_id,)
        )
        conn.commit()

        return get_active_model()


def create_chaeacters_table():
    schema = '''
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        prompt TEXT NOT NULL
    );
    '''

    with _connect() as conn:
        conn.executescript(schema)


def list_characters() -> list[dict[str, str | int]]:
    with _connect() as conn:
        cur = conn.execute(
            '''SELECT id, name FROM characters
            ORDER BY id'''
        )
        rows = cur.fetchall()

        return [{
            'id': row['id'],
            'name': row['name']
        } for row in rows]


def get_character_by_id(character_id: int) -> dict[str, str | int] | None:
    with _connect() as conn:
        cur = conn.execute(
            '''SELECT id, name, prompt FROM characters
            WHERE id=?''',
            (character_id,)
        )
        row = cur.fetchone()

        return {
            'id': row['id'],
            'name': row['name'],
            'prompt': row['prompt']
        } if row else None


def get_character_prompt_for_user(user_id: int) -> str:
    return get_user_character(user_id)['prompt']


def create_user_character_links_table():
    schema = '''
    CREATE TABLE IF NOT EXISTS user_character (
    user_id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0, 1)),
    FOREIGN KEY(character_id) REFERENCES characters(id)
    );
    '''

    with _connect() as conn:
        conn.executescript(schema)


def set_user_character(user_id: int, character_id: int) -> dict[str, str | int] | None:
    character = get_character_by_id(character_id)

    if not character:
        raise ValueError('Неизвестный ID персонажа')

    with _connect() as conn:
        conn.execute(
            '''INSERT INTO user_character (user_id, character_id)
            VALUES(?, ?)
            ON CONFLICT (user_id)
            DO UPDATE SET character_id = excluded.character_id''',
            (user_id, character_id)
        )

    return character


def get_user_character(user_id: int) -> dict[str, str | int] | None:
    with _connect() as conn:
        row = conn.execute(
            '''SELECT p.id, p.name, p.prompt
            FROM user_character up
            JOIN characters p ON p.id = up.character_id
            WHERE up.user_id = ?''',
            (user_id,)
        ).fetchone()

        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'prompt': row['prompt']
            }

        row = conn.execute(
            '''SELECT id, name, prompt FROM characters
            WHERE id=1'''
        ).fetchone()

        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'prompt': row['prompt']
            }

        row = conn.execute(
            '''SELECT id, name, prompt FROM characters
            ORDER BY id LIMIT 1'''
        ).fetchone()

        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'prompt': row['prompt']
            }

        raise RuntimeError('Таблица characters пуста.')


def init_db():
    create_notes_table()
    create_models_table()
    create_chaeacters_table()
    create_user_character_links_table()

    logger.info('Database initialized.')