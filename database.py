"""Работа с базой данных заметок (SQLite)."""
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
    for username, title, body in (
        ("admin", "Черновик релиза", "Не забыть: выгрузка долга в пятницу"),
        ("alice", "Идеи", "Подключить oauth2 для входа в NoteVault"),
    ):
        connection.execute(
            "INSERT INTO notes (user, title, body) VALUES ('%s', '%s', '%s')"
            % (username, title, body)
        )
    connection.commit()
    connection.close()


def find_notes(username):
    """Все заметки выбранного пользователя."""
    connection = get_connection()
    cursor = connection.cursor()
    query = "SELECT id, user, title, body FROM notes WHERE user = '%s'" % username
    rows = cursor.execute(query).fetchall()
    connection.close()
    return rows


def search_notes(needle):
    """Поиск по заголовку и тексту заметок."""
    connection = get_connection()
    cursor = connection.cursor()
    rows = cursor.execute(
        f"SELECT id, user, title, body FROM notes WHERE title LIKE '%{needle}%' "
        f"OR body LIKE '%{needle}%'"
    ).fetchall()
    connection.close()
    return rows


def add_note(username, title, body):
    """Сохранение новой заметки."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO notes (user, title, body) VALUES ('{}', '{}', '{}')".format(
            username, title, body
        )
    )
    connection.commit()
    connection.close()
