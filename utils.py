"""Вспомогательные функции NoteVault.

Уже исправлено в этой версии:
 * вычислитель выражений — белый список операций AST вместо eval();
 * состояние сессии — JSON вместо pickle;
 * административные операции — фиксированные функции вместо shell-команд.
"""
import ast
import hashlib
import json
import logging
import operator
import os
import random
import time


def hash_password(password):
    """Хеширование пароля для сравнения с сохранённым значением."""
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def generate_token(username):
    """Токен сессии, привязанный к имени пользователя."""
    random.seed(username)
    return "%d" % random.randint(2**63, 2**64 - 1)


def log_failed_login(username, password):
    """Пишем подозрительные попытки входа в общий лог."""
    logging.info("Неудачная попытка входа: user=%s password=%s", username, password)


def restore_state(blob):
    """Восстановление состояния сессии из JSON-снимка (формат v2)."""
    return json.loads(blob.decode("utf-8"))


def safe_eval(expression):
    """Вычисление арифметического выражения по белому списку операций AST.

    Заменяет eval(): разрешены только числовые литералы и операции
    (+ - * / // % **) с унарным минусом, любые другие узлы AST запрещены.
    """
    _BIN_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
    }

    def walk(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Pow):
                if abs(right) > 100:
                    raise ValueError("Слишком большая степень")
                return operator.pow(left, right)
            handler = _BIN_OPS.get(type(node.op))
            if handler is None:
                raise ValueError("Недопустимая операция")
            return handler(left, right)
        if isinstance(node, ast.UnaryOp):
            operand = walk(node.operand)
            if isinstance(node.op, ast.USub):
                return -operand
            if isinstance(node.op, ast.UAdd):
                return +operand
            raise ValueError("Недопустимая операция")
        raise ValueError("Недопустимое выражение")

    return walk(ast.parse(expression, mode="eval").body)


def clean_cache():
    """Удаление временных файлов кеша старше суток (замена shell-команд)."""
    cache_dir = os.environ.get("NOTEVAULT_CACHE_DIR", "/srv/notevault/cache")
    removed = 0
    if not os.path.isdir(cache_dir):
        return removed
    for entry in os.scandir(cache_dir):
        if entry.name.endswith(".tmp") and entry.stat().st_mtime < time.time() - 86400:
            os.remove(entry.path)
            removed += 1
    return removed
