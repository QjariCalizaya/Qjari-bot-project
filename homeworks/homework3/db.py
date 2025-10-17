import os
import sqlite3
from dotenv import load_dotenv
from datetime import datetime, date
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
    """
    with _connect() as conn:
        conn.executescript(schema)


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

def find_notes(user_id : int , text:str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            """SELECT id, text, created_at
            FROM notes
            WHERE user_id = ?
            AND text LIKE '%'|| ? || '%' 
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

def count_note(user_id: int):
    with _connect() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE user_id = ?",
            (user_id,)
        )
    
    row = cur.fetchone()
    return row[0] if row else 0

# возвращает текст со всей активностью за последние 7 дней
def activity_note(user_id:int):
    with _connect() as conn:
        cur = conn.execute(
            "SELECT created_at FROM notes WHERE user_id = ?",
            (user_id, )
        )
        dataTime = [datetime.fromisoformat(row["created_at"]) for row in cur.fetchall()]
    
    # список активности по дням недели (0=понедельник, 6=воскресенье)
    activityInDays = [0,0,0,0,0,0,0]
    for day in dataTime:
        activityInDays[day.weekday()] += 1
    return activityToASCII(activityInDays)
    
# форматирует числа с помощью ASCII для отображения активности
def activityToASCII(activityInDays):
    text = "активность:"
    left = "-"
    right = "-|"
    days = ["M","T","W","T","F","S","S"]
    today = date.today().weekday() + 1
    step = today
    stop = today
    text += "\n|"
    
    # создание верхней линии с днями недели
    while True:
        if step > 6 : step = 0
        text = text + left + days[step] + right
        step+=1
        if step == stop : 
            text+="\n|"
            break
    
    # добавление количества активности под соответствующими днями
    step = today
    while True:
        if step > 6 : step = 0
        text+=  parseIntToString(activityInDays[step]) + "|"
        step+=1
        if step == stop : 
            break

    return text
    
# определяет формат отображения числа --1, -10, 100
def parseIntToString(number):

    digits = len(str(number))
    #print(digits)
    
    if(digits==3):
        return number
    if(digits==2):
        return f"-{number}"
    if(digits==1):
        return f"--{number}"
