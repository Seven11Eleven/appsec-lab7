"""NoteVault — внутренний сервис заметок для команды разработки.

Версия после security review: все уязвимости из отчётов SAST/SCA исправлены.
См. README (раздел «Маппинг уязвимостей → фиксы») и отчёты reports/*after*.
"""
import base64
import os

import requests
import yaml
from flask import Flask, abort, redirect, render_template, request, session

import database
import utils
from config import UPDATES_URL, UPLOAD_DIR

app = Flask(__name__)
app.config.from_pyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py"))

database.init_db()


@app.route("/")
def index():
    """Главная страница: список заметок выбранного пользователя."""
    user = request.args.get("user", "admin")
    return render_template("index.html", user=user, notes=database.find_notes(user))


@app.route("/notes/add", methods=["POST"])
def notes_add():
    """Добавление новой заметки в базу."""
    database.add_note(request.form["user"], request.form["title"], request.form["body"])
    return redirect("/")


@app.route("/search")
def search():
    """Поиск по заметкам: запрос попадает в шаблон с автоэскейпом (защита от XSS)."""
    query = request.args.get("q", "")
    return render_template("search.html", query=query, notes=database.search_notes(query))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Вход в сервис: сравнение PBKDF2-хеша через compare_digest, без утечки таймингов."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and utils.verify_admin_password(password):
            session["user"] = username
            session["token"] = utils.generate_token(username)
            return redirect("/")
        utils.log_failed_login(username)
        return render_template("login.html", error="Неверное имя пользователя или пароль"), 401
    return render_template("login.html")


@app.route("/calc")
def calc():
    """Простой вычислитель выражений: безопасный AST-эвалюатор вместо eval."""
    expression = request.args.get("expr", "0")
    try:
        result = utils.safe_eval(expression)
    except (ValueError, SyntaxError, TypeError, OverflowError, ZeroDivisionError):
        return {"error": "Некорректное выражение"}, 400
    return {"result": result}


@app.route("/import", methods=["POST"])
def import_notes():
    """Импорт заметок из YAML: используется только safe_load."""
    payload = yaml.safe_load(request.form.get("yaml", ""))
    if not isinstance(payload, list):
        return {"error": "Ожидался список заметок"}, 400
    for note in payload:
        if not isinstance(note, dict):
            return {"error": "Заметка должна быть отображением (dict)"}, 400
        database.add_note(str(note.get("user", "")), str(note.get("title", "")), str(note.get("body", "")))
    return redirect("/")


@app.route("/updates")
def updates():
    """Прокси к API обновлений: клиент меняет только путь на доверенном хосте (защита от SSRF)."""
    path = request.args.get("path", "/")
    if not path.startswith("/") or ".." in path:
        abort(400, description="Недопустимый путь")
    response = requests.get(f"{UPDATES_URL}{path}", timeout=10)
    return response.text


@app.route("/files")
def files():
    """Отдача вложения: realpath ограничен каталогом UPLOAD_DIR (защита от path traversal)."""
    name = request.args.get("name", "")
    base = os.path.realpath(UPLOAD_DIR)
    candidate = os.path.realpath(os.path.join(base, os.path.basename(name)))
    if candidate != base and not candidate.startswith(base + os.sep):
        abort(400, description="Недопустимое имя файла")
    if not os.path.isfile(candidate):
        abort(404)
    with open(candidate, "r", encoding="utf-8", errors="replace") as fd:
        return fd.read()


@app.route("/export")
def export():
    """Финальный редирект: только локальные относительные пути (защита от open redirect)."""
    next_url = request.args.get("next", "/")
    if not next_url.startswith("/") or next_url.startswith("//") or "\\" in next_url:
        abort(400, description="Недопустимый redirect")
    return redirect(next_url)


@app.route("/restore", methods=["POST"])
def restore():
    """Восстановление состояния сессии из JSON-снимка (формат v2)."""
    blob = base64.b64decode(request.cookies.get("state", "e30="))
    try:
        state = utils.restore_state(blob)
    except ValueError:
        abort(400, description="Некорректный снимок состояния")
    return {"state": state}


@app.route("/admin/maintenance", methods=["POST"])
def maintenance():
    """Административные операции: фиксированный список действий вместо shell-команд."""
    action = request.form.get("action", "")
    if action == "clean_cache":
        return {"removed": utils.clean_cache()}
    if action == "vacuum_db":
        database.vacuum()
        return {"ok": True}
    abort(400, description="Неизвестная административная операция")


if __name__ == "__main__":
    # Режим отладки включается только переменной окружения NOTEVAULT_DEBUG (см. config.py).
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
