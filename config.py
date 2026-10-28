"""Конфигурация NoteVault (версия после security review).

Секреты не хранятся в коде: всё, что раньше было константами, вынесено в
переменные окружения (OWASP A07:2021). Режим отладки включается только
переменной окружения (A05:2021). Жёстко прописанный админ-пароль заменён
на хеш PBKDF2 в переменной окружения.
"""
import os
import secrets

# Секрет сессии задаётся при деплое; если переменной нет, ключ генерируется заново.
# NOTE: при перезапуске незаведённый через env инстанс сбрасывает сессии —
# в проде NOTEVAULT_SECRET_KEY обязателен.
SECRET_KEY = os.environ.get("NOTEVAULT_SECRET_KEY", "") or secrets.token_hex(32)

# Хеш пароля администратора: PBKDF2-HMAC-SHA256 (utils.hash_password) в hex.
# Генерируется один раз: python -c "from utils import hash_password; print(hash_password('<пароль>'))"
ADMIN_PASSWORD_HASH = os.environ.get("NOTEVAULT_ADMIN_PASSWORD_HASH", "")

# Соль для PBKDF2 (публичная, но иммутабельная на время жизни базы учётных записей).
PASSWORD_SALT = os.environ.get("NOTEVAULT_PASSWORD_SALT", "notevault-default-salt-v1")

# Режим отладки включается только переменной окружения.
DEBUG = os.environ.get("NOTEVAULT_DEBUG", "0") == "1"

# База SQLite сервиса.
DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notevault.db")

# Каталог вложений заметок.
UPLOAD_DIR = os.environ.get("NOTEVAULT_UPLOAD_DIR", "/srv/notevault/uploads")

# Адрес API обновлений: клиент может менять только путь, но не хост.
UPDATES_URL = os.environ.get("NOTEVAULT_UPDATES_API", "https://updates.notevault.corp/api/v1")
