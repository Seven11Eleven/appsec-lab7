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

Для ветки `fix/security` (обновлённые зависимости) нужен Python ≥ 3.10 — используйте
системный `/usr/bin/python3.11` или `python3.13` (на pyenv-3.9 новые urllib3/requests
недоступны). На ветке `main` (старые зависимости) достаточно и `python3` (3.9).

```bash
python3.11 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# обязательные переменные окружения (секреты не в коде):
export NOTEVAULT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"

# хеш пароля админа (PBKDF2): сгенерировать и передать в сервис
export NOTEVAULT_ADMIN_PASSWORD_HASH="$(python -c "from utils import hash_password; print(hash_password('Цепкий_пароль_2024'))")"

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

## Результаты первичного сканирования (main, до фиксов)

Отчёты лежат в `reports/` (снимок задокументирован отдельным коммитом, см. историю):
- **SAST (semgrep, p/python + p/secrets)**: 14 находок — XSS (`raw-html-format`), `eval` → RCE
  (`user-eval`, `eval-injection`), SSRF (`ssrf-requests`), `debug=True` + `host 0.0.0.0`
  (`debug-enabled`, `avoid_app_run_with_bad_host`), MD5 для паролей (`insecure-hash-algorithms-md5`,
  `md5-used-as-password`), пароль в логах (`python-logger-credential-disclosure`), `shell=True`
  (`subprocess-shell-true`);
- **SAST (bandit)**: 12 issues (3 High, 9 Medium) — в т.ч. SQL-инъекции (B608), pickle.loads (B301),
  yaml.load (B506), eval (B307), hardcoded секреты (B105), bind 0.0.0.0 (B104);
- **SCA (pip-audit)**: 33 известные уязвимости (CVE/PYSEC) в 6 упаковках из `requirements.txt`
  (Flask, Werkzeug, Jinja2, requests, urllib3, gunicorn).

Скрины/файлы: `reports/sast-initial.{txt,json,sarif}`, `reports/sast-bandit-initial.{txt,json}`,
`reports/sca-initial.md`.

> Сканирования воспроизводятся командами из раздела «Как защитить лабу».
> SAST-сканы (semgrep, bandit) запускаются на своём Python; для SCA нужен Python ≥ 3.10
> (в CI установлен 3.12), т.к. новые версии запросов к пакетам требуют соответствующие interpreter.

## Результаты повторного сканирования (fix/security, после фиксов)

| Скан | До (main) | После (fix/security) | Отчёты |
|---|---|---|---|
| SAST semgrep (p/python + p/secrets) | 14 findings | **0 findings** | `sast-initial.txt|json` → `sast-after.txt|json` |
| SAST bandit | 12 issues | **No issues identified** | `sast-bandit-initial.*` → `bandit-after.txt|json` |
| SCA pip-audit | 33 уязвимости в 6 пакетах | **No known vulnerabilities found** | `sca-initial.md` → `sca-after.md|json` |

## Маппинг уязвимость → исправление (фиксы в PR)

| Проблема | Класс | Где было | Исправление (коммит в PR) |
|---|---|---|---|
| SQL-инъекция | A03:2021 | `database.py` (`init_db`, `find_notes`, `search_notes`, `add_note`) | плейсхолдеры `?` вместо `%`/f-string/`format` — `8469a43` |
| `eval` → RCE | A06/A05 | `app.py /calc` | AST-эвалюатор по белому списку операций (`utils.safe_eval`) — `6dd2f8f` |
| Insecure deserialization (pickle) | A08:2021 | `app.py /restore`, `utils.py restore_state` | снапшоты сессии — JSON, pickle убран — `6dd2f8f` |
| YAML RCE | A08:2021 | `app.py /import` (`FullLoader`) | `yaml.safe_load` + проверка структуры — `6dd2f8f` |
| Shell injection | A03:2021 | `utils.py run_maintenance`, `app.py /admin/maintenance` | только фиксированные операции (`clean_cache`/`vacuum_db`), `shell=True` удалён — `6dd2f8f` |
| Слабое хеширование паролей (MD5) | A02:2021 | `utils.py hash_password` | PBKDF2-HMAC-SHA256 (310k iter, соль из env) — `1ba51f3` |
| Токены через `random` | A02:2021 | `utils.py generate_token` | `secrets.token_hex(32)` — `1ba51f3` |
| Пароль в логах | A09:2021 | `utils.py log_failed_login` | логируется только имя пользователя — `1ba51f3` |
| Секреты в коде | A07:2021 | `config.py` (SECRET_KEY, ADMIN_PASSWORD) | env-переменные (`NOTEVAULT_SECRET_KEY`, `NOTEVAULT_ADMIN_PASSWORD_HASH`) — `1ba51f3` |
| XSS | A03:2021 | `app.py /search` (`render_template_string`, ручной HTML) | `render_template` + автоэскейп (`templates/search.html`) — `b92d384` |
| SSRF | A10:2021 | `app.py /updates` (`requests.get` по url от клиента) | URL целиком на сервере, клиент задаёт только `since`-параметр + `timeout` — `b92d384`, `bde8f22` |
| Path traversal | A01:2021 | `app.py /files` (`os.path.join` + `open`) | `basename` + `realpath`-проверка внутри `UPLOAD_DIR` — `b92d384` |
| Open redirect | A01:2021 | `app.py /export` | redirect только локальных относительных путей — `b92d384` |
| Debug=True в проде | A05:2021 | `app.py`, `config.py` | `DEBUG` из env (по умолчанию False), host 127.0.0.1 — `b92d384` |
| Устаревшие зависимости (CVE) | A06:2021 | `requirements.txt` (Flask 2.2.2, Werkzeug 2.2.2, Jinja2 3.1.2, requests 2.28.1, urllib3 1.26.7, gunicorn 20.1.0) | актуальные пины без известных CVE — `0b47f45` |
