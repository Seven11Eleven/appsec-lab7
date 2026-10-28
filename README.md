# NoteVault (Lab #7 — AppSec full review)

Учебный репозиторий для лабораторной работы №7 по безопасности приложений:
полный цикл анализа — SAST, SCA, исправление уязвимостей через pull request и Code Review.

NoteVault — маленький внутренний сервис заметок (Flask + SQLite): список заметок,
поиск, вход, импорт/экспорт, служебные админ-эндпоинты.

## Структура

```
app.py          — HTTP-эндпоинты Flask
config.py       — конфигурация сервиса
database.py     — доступ к SQLite
utils.py        — утилиты и административные команды
templates/      — HTML-страницы
requirements.txt— зафиксированные зависимости
reports/        — результаты SAST/SCA-сканирования
```

## Запуск (локально)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python app.py
# или: gunicorn -w 2 app:app -b 127.0.0.1:5000
```

Затем: http://127.0.0.1:5000

## Как защитить лабу (скрипт)

1. Что значит SAST? — статический анализ нашего исходного кода: **semgrep**.
2. Что значит SCA? — анализ сторонних зависимостей (requirements.txt) на известные CVE: **pip-audit**.
3. Отчёты лежат в `reports/` (они же воспроизводятся командами ниже).
4. Уязвимости кода исправлены в ветке `fix/security` → **Pull Request** `fix/security → main`,
   после фиксов SAST/SCA чистые (отчёты `reports/*after*`).

### SAST (semgrep)

```bash
pip install semgrep
semgrep scan --config p/python --config p/secrets --exclude reports --text
# JSON/SARIF-вариант:  semgrep scan --config p/python --config p/secrets --sarif -o reports/sast.sarif
```

### SCA (pip-audit)

```bash
pip install pip-audit
pip-audit -r requirements.txt -f markdown
# если зависимости уже установлены в venv:
pip-audit -f markdown
```

### CI

GitHub Actions (`.github/workflows/security.yml`) и GitLab CI (`.gitlab-ci.yml`)
запускают semgrep + pip-audit на каждый push и PR и выкладывают отчёты артефактами.

### Порядок работы для лабы

```bash
git push origin main
git push origin fix/security
# на GitHub/GitLab создать PR/MR: fix/security → main
# CI приложит отчёты по изменениям, редьвьюер (одногруппник) оставит Code Review
```

## Что мы фиксим (summary)

| Проблема | Класс OEM | Endpoints/файлы |
|---|---|---|
| SQL-инъекция | A03:2021 | `database.py` (`find_notes`, `search_notes`, `add_note`) |
| XSS | A03:2021 | `app.py /search` |
| `eval` → RCE | A06/A05 | `app.py /calc` |
| Insecure deserialization (pickle) | A08:2021 | `app.py /restore`, `utils.py` |
| YAML RCE | A08:2021 | `app.py /import` |
| SSRF | A10:2021 | `app.py /updates` |
| Path traversal | A01:2021 | `app.py /files` |
| Open redirect | A01:2021 | `app.py /export` |
| Shell injection | A03:2021 | `utils.py run_maintenance`, `app.py /admin/maintenance` |
| Слабое хеширование паролей (MD5) | A02:2021 | `utils.py` |
| Токены через `random` | A02:2021 | `utils.py generate_token` |
| Секреты в коде | A07:2021 | `config.py` |
| Пароль в логах | A09:2021 | `utils.py log_failed_login` |
| Debug=True в проде | A05:2021 | `app.py`, `config.py` |
| Устаревшие зависимости (CVE) | A06:2021 | `requirements.txt` |
