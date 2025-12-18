import os
import sqlite3
from typing import Any, Optional
import config
import logger as log
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "bot.db")

def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY,
        key TEXT NOT NULL UNIQUE,
        label TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0,1))
    );

    CREATE UNIQUE INDEX IF NOT EXISTS ux_models_single_active ON models(active) WHERE active=1;

    INSERT OR IGNORE INTO models(id, key, label, active) VALUES
    (1, 'deepseek/deepseek-chat-v3.1:free', 'DeepSeek V3.1 (free)', 1),
    (2, 'deepseek/deepseek-r1:free', 'DeepSeek R1 (free)', 0),
    (3, 'mistralai/mistral-small-24b-instruct-2501:free', 'Mistral Small 24b (free)', 0),
    (4, 'meta-llama/llama-3.1-8b-instruct:free', 'Llama 3.1 8B (free)', 0);
    """

    schema2 = """
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        prompt TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS user_character (
        telegram_user_id INTEGER PRIMARY KEY,
        character_id INTEGER NOT NULL,
        FOREIGN KEY(character_id) REFERENCES characters(id)
    );

    INSERT OR IGNORE INTO characters(id, name, prompt) VALUES
      (1,'Йода','...'),
      (2,'Дарт Вейдер','...'),
      (3,'Мистер Спок','...'),
      (4,'Тони Старк','...'),
      (5,'Шерлок Холмс','...'),
      (6,'Капитан Джек Воробей','...'),
      (7,'Гэндальф','...'),
      (8,'Винни-Пух','...'),
      (9,'Голум','...'),
      (10,'Рик','...'),
      (11,'Бендер','...');
    """

    schema3="""
    CREATE TABLE IF NOT EXISTS service_call_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        service TEXT NOT NULL,
        request TEXT NOT NULL,
        response TEXT,
        status_code INTEGER,
        duration_ms INTEGER,
        error TEXT
    );
    CREATE TABLE IF NOT EXISTS error_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        level TEXT NOT NULL,
        logger TEXT NOT NULL,
        message TEXT NOT NULL,
        user_id INTEGER,
        command TEXT,
        details TEXT
    
    );
    
    """

    schema4 = """
    CREATE TABLE IF NOT EXISTS settings(
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    maxNotes INTEGER NOT NULL

    );
    CREATE TABLE IF NOT EXISTS feature_toggles(
        name TEXT PRIMARY KEY,
        enabled INTEGER NOT NULL CHECK (enabled IN (0,1))
    );
    """

    with _connect() as conn:
        conn.executescript(schema)
        conn.executescript(schema2)
        conn.executescript(schema3)
        conn.executescript(schema4)


def add_note(user_id: int, text: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO notes(user_id, text) VALUES (?, ?)",
            (user_id, text)
        )
        return cur.lastrowid


def list_notes(user_id: int, limit: int = 10):
    with _connect() as conn:
        cur = conn.execute(
            """SELECT id, text, created_at
            FROM notes
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?""",
            (user_id, limit)
        )
        return cur.fetchall()


def find_notes(user_id: int, text: str):
    with _connect() as conn:
        cur = conn.execute(
            """SELECT id, text, created_at
               FROM notes
               WHERE user_id = ? AND text LIKE '%' || ? || '%'
               ORDER BY id DESC
               LIMIT 10;""",
            (user_id, text)
        )
        return cur.fetchall()


def update_note(user_id: int, note_id: int, text: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            """UPDATE notes
               SET text = ?
               WHERE user_id = ? AND id = ?""",
            (text, user_id, note_id)
        )
        return cur.rowcount > 0


def delete_note(user_id: int, note_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM notes WHERE user_id = ? AND id = ?",
            (user_id, note_id)
        )
        return cur.rowcount > 0


def list_models() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT id, key, label, active FROM models ORDER BY id").fetchall()
        return [{"id": r["id"], "key": r["key"], "label": r["label"], "active": bool(r["active"])} for r in rows]


def get_active_model() -> dict:
    with _connect() as conn:
        row = conn.execute("SELECT id, key, label FROM models WHERE active=1").fetchone()
        if row:
            return {"id": row["id"], "key": row["key"], "label": row["label"], "active": True}
        row = conn.execute("SELECT id, key, label FROM models ORDER BY id LIMIT 1").fetchone()
        if not row:
            raise RuntimeError("В реестре моделей нет записей")
        conn.execute("UPDATE models SET active=CASE WHEN id=? THEN 1 ELSE 0 END", (row["id"],))
        return {"id": row["id"], "key": row["key"], "label": row["label"], "active": True}

def get_model_key_by_ID(id:int)-> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT key FROM models WHERE id =?", (id,)).fetchone()
        if row:
            return {"key": row["key"]}
        if not row:
            raise RuntimeError("id неправильный")
        return None


def set_active_model(model_id: int) -> dict:
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        exists = conn.execute("SELECT 1 FROM models WHERE id=?", (model_id,)).fetchone()
        if not exists:
            conn.rollback()
            raise ValueError("Неизвестный ID модели")
        
        # Asegúrate de primero desactivar todos los activos
        conn.execute("UPDATE models SET active=0")
        conn.execute("UPDATE models SET active=1 WHERE id=?", (model_id,))
        conn.commit()
    return get_active_model()


def list_characters() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT id, name FROM characters ORDER BY id").fetchall()
        return [{"id": r["id"], "name": r["name"]} for r in rows]


def get_character_by_id(character_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, name, prompt FROM characters WHERE id=?",
            (character_id,)
        ).fetchone()
    return {"id": row["id"], "name": row["name"], "prompt": row["prompt"]} if row else None


def set_user_character(user_id: int, character_id: int) -> dict:
    character = get_character_by_id(character_id)
    if not character:
        raise ValueError("Неизвестный ID персонажа")
    with _connect() as conn:
        conn.execute("""
        INSERT INTO user_character(telegram_user_id, character_id)
        VALUES(?, ?)
        ON CONFLICT(telegram_user_id) DO UPDATE SET character_id=excluded.character_id
        """, (user_id, character_id))
    return character


def get_user_character(user_id: int) -> dict:
    with _connect() as conn:
        row = conn.execute("""
        SELECT p.id, p.name, p.prompt
        FROM user_character uc
        JOIN characters p ON p.id = uc.character_id
        WHERE uc.telegram_user_id = ?
        """, (user_id,)).fetchone()

        if row:
            return {"id": row["id"], "name": row["name"], "prompt": row["prompt"]}

        row = conn.execute("SELECT id, name, prompt FROM characters WHERE id=1").fetchone()
        if row:
            return {"id": row["id"], "name": row["name"], "prompt": row["prompt"]}

        row = conn.execute("SELECT id, name, prompt FROM characters ORDER BY id LIMIT 1").fetchone()
        if not row:
            raise RuntimeError("Таблица characters пуста")

        return {"id": row["id"], "name": row["name"], "prompt": row["prompt"]}


def get_character_prompt_for_user(user_id: int)-> str:
    return get_user_character(user_id)["prompt"]


def write_service_call(
        service: str,
        request: str,
        response: Optional[str],
        status_code: Optional[int],
        duration_ms: Optional[int],
        error: Optional[str] = None,
)-> None:
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO service_call_log
                (created_at, service , request, response, status_code, duration_ms, error)
            VALUES (?,?,?,?,?,?,?)
            """,(
                datetime.utcnow().isoformat(timespace="seconds"),
                service,
                request,
                response,
                status_code,
                duration_ms,
                error,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.error("не удалось записать запись в service_call_log", e, exc_info=True)



def write_error_call(
        level: str,
        logger_name: str,
        message: str,
        user_id : Optional[int] = None,
        command: Optional[str] = None,
        details: Optional[str] = None,
)-> None:
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO service_call_log
                (created_at, level , logger, message, user_id, command, details)
            VALUES (?,?,?,?,?,?,?)
            """,(
                datetime.utcnow().isoformat(timespace="seconds"),
                level,
                logger_name,
                message,
                user_id,
                command,
                details,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.error("не удалось записать запись в error_logs: %s", e, exc_info=True)

def write_error_log(
    level: str,
    logger_name: str,
    message: str,
    user_id: Optional[int] = None,
    command: Optional[str] = None,
    details: Optional[str] = None,
) -> None:
    """
    Записать одну строку в таблицу error_log.

    Используем для важных ошибок:
    - OpenRouterError (401/429/5xx),
    - серьезные ошибки БД,
    - падения хендлеров
    """
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO error_log (created_at, level, logger, message, user_id, command, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(timespec="seconds"),
                level,
                logger_name,
                message,
                user_id,
                command,
                details,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.error("Не удалось записать ошибку в error_log: %s", e, exc_info=True)


def get_setting_or_default(key: str, default: str)->str:
    with _connect() as conn:
        row = conn.execute(
           " SELECT value FROM settings WHERE key = ?",
           (key,),
        ).fetchone()
    if row is None:
        return default
    return row['value']

def get_int_setting(key: str, default: int)-> int:
    raw = get_setting_or_default(key,str(default))
    try:
        return int(raw)
    except ValueError:
        return default
    
def get_bool_setting(key: str, default: bool)->bool:
    raw = get_setting_or_default(key, "true" if default else "false")
    raw_low = raw.lower()
    if raw_low in ("1", "true", "yes", "on"):
        return True
    if raw_low in ("0", "false" , "no", "off"):
        return False
    return default
 

def is_feature_enabled(name:str, default: bool)-> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT enabled FROM feature_toggles WHERE name = ?",
            (name,),
        ).fetchone()
    if row is None:
        return default

    return bool(row["enabled"])

def set_settings(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO  settings (key, value) VALUES (?, ?)"
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key,value),
        )

def set_feature_toggle(name:str,enabled:bool)->None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO features_toggles(name,enabled)
            VALUES(? , ?)
            ON CONFLICT(name) DO UPDATE SET enabled = excluded.enabled
            """,
            (name,1 if enabled else 0),
        )




if __name__ == "__main__":
    init_db()
    print("ok")
