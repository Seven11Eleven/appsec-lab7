"""NoteVault — внутренний сервис заметок для команды разработки."""
import base64
import os

import requests
import yaml
from flask import Flask, abort, redirect, render_template, render_template_string, request, session

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
    notes = database.find_notes(user)
    return render_template("index.html", user=user, notes=notes)


@app.route("/notes/add", methods=["POST"])
def notes_add():
    """Добавление новой заметки в базу."""
    database.add_note(request.form["user"], request.form["title"], request.form["body"])
    return redirect("/")


@app.route("/search")
def search():
    """Поиск по заметкам, результаты отдаются как готовый HTML-сниппет."""
    query = request.args.get("q", "")
    found = database.search_notes(query)
    html = "<h1>Результаты поиска: %s</h1><ul>" % query
    for row in found:
        html += "<li>%s</li>" % row[2]
    html += "</ul>"
    return render_template_string(html)


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
    """Прокси к серверу обновлений: подтягиваем изменения из внешнего источника."""
    url = request.args.get("url", UPDATES_URL)
    response = requests.get(url)
    return response.text


@app.route("/files")
def files():
    """Отдача вложения заметки на скачивание."""
    name = request.args.get("name", "")
    path = os.path.join(UPLOAD_DIR, name)
    with open(path, "r", encoding="utf-8", errors="replace") as fd:
        return fd.read()


@app.route("/export")
def export():
    """Перенаправление после экспорта заметок (ссылку зашивает фронтенд)."""
    next_url = request.args.get("next", "/")
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
    app.run(host="0.0.0.0", port=5000, debug=True)
