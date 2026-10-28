"""Работа с базой данных заметок (SQLite).

Версия после security review: все запросы параметризованы, пользователю не
позволено влиять на текст SQL (OWASP A03:2021 — Injection).
"""
import sqlite3

from config import DATABASE_FILE


def get_connection():
    connection = sqlite3.connect(DATABASE_FILE)
    return connection


def init_db():
    """Создание схемы и первичное наполнение демо-данными."""
    connection = get_connection()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL
        )
        """
    )
    rows = (
        ("admin", "Черновик релиза", "Не забыть: выгрузка долга в пятницу"),
        ("alice", "Идеи", "Подключить oauth2 для входа в NoteVault"),
    )
    connection.executemany(
        "INSERT INTO notes (user, title, body) VALUES (?, ?, ?)", rows
    )
    connection.commit()
    connection.close()


def find_notes(username):
    """Все заметки выбранного пользователя (параметризованный запрос)."""
    connection = get_connection()
    cursor = connection.cursor()
    rows = cursor.execute(
        "SELECT id, user, title, body FROM notes WHERE user = ?", (username,)
    ).fetchall()
    connection.close()
    return rows


def search_notes(needle):
    """Поиск по заголовку и тексту заметок (параметризованный запрос)."""
    connection = get_connection()
    cursor = connection.cursor()
    pattern = f"%{needle}%"
    rows = cursor.execute(
        "SELECT id, user, title, body FROM notes WHERE title LIKE ? OR body LIKE ?",
        (pattern, pattern),
    ).fetchall()
    connection.close()
    return rows


def add_note(username, title, body):
    """Сохранение новой заметки (параметризованный запрос)."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO notes (user, title, body) VALUES (?, ?, ?)",
        (username, title, body),
    )
    connection.commit()
    connection.close()


def vacuum():
    """Обслуживание базы: сжатие файла БД."""
    connection = get_connection()
    connection.execute("VACUUM")
    connection.close()
