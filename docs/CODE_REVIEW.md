# Code Review — PR `fix/security` → `main`

- Ревьюер: **@Seven11Eleven** (self-review)
- Дата: 2026-10-29
- Объект ревью: диффик `Files changed` PR — 10 коммитов (7 fix-коммитов, отчёты до/после,
  CI-фикс), лог запусков Actions, артефакты `sast-report` и `sca-report`,
  файлы `reports/sast-after.*`, `reports/bandit-after.*`, `reports/sca-after.*`.

## 1. Методика ревью

1. Построчный просмотр диффа по чек-листу AppSec (см. шаблон PR).
2. Воспроизводимость: сканы можно повторить локально по командам README
   (semgrep `p/python` + `p/secrets`, bandit, `pip-audit -r requirements.txt`).
3. Сверка с прогонами CI: `Findings: 0` у semgrep, `No issues identified` у bandit,
   `No known vulnerabilities found` у pip-audit.

## 2. Проверка по чек-листу

| # | Пункт чек-листа | Результат | Подтверждение в коде |
|---|---|---|---|
| 1 | SQL-запросы параметризованы | ✅ | `database.py`: `execute(sql, (…))` c плейсхолдерами `?`; `init_db` использует `executemany` |
| 2 | Нет `eval`/`pickle.loads`/`yaml.load` без `SafeLoader` | ✅ | `/calc` → `utils.safe_eval` (AST, белый список операций); `/restore` — JSON; `/import` — `yaml.safe_load` |
| 3 | Секреты в env, не в коде | ✅ | `config.py`: `NOTEVAULT_SECRET_KEY`, `NOTEVAULT_ADMIN_PASSWORD_HASH`, `NOTEVAULT_DEBUG`, `NOTEVAULT_PASSWORD_SALT` |
| 4 | Нет SSRF | ✅ | `/updates`: адрес из константы `UPDATES_URL`, клиент формирует только `params={"since": …}`, присутствует `timeout=10` |
| 5 | Нет path traversal | ✅ | `/files`: `os.path.basename` + `os.path.realpath` + проверка префикса `UPLOAD_DIR` + `os.path.isfile` |
| 6 | Нет open redirect | ✅ | `/export`: только локальные относительные пути (отбраковка `//`, `\`, абсолютных) |
| 7 | Пароли хешируются PBKDF2, токены `secrets` | ✅ | `utils.hash_password` = `pbkdf2_hmac` (310 000 итераций, соль из env); `verify_admin_password` — `hmac.compare_digest`; `generate_token` — `secrets.token_hex(32)` |
| 8 | Нет `shell=True` | ✅ | `/admin/maintenance` диспетчеризует `clean_cache`/`vacuum_db`; `subprocess.run(..., shell=True)` удалён из `utils.py` |
| 9 | Пароль не в логах | ✅ | `log_failed_login(username)` — только имя пользователя |
| 10 | `debug=False` в проде | ✅ | `app.run(host="127.0.0.1", debug=app.config.get("DEBUG", False))`; `DEBUG` включается только переменной окружения |

## 3. История доработок в рамках ревью

Первая версия фикса `/updates` (`b92d384`) валидировала путь, но повторный semgrep-скан
показал оставшуюся taint-находку (`ssrf-injection-requests`). В `bde8f22` архитектура
переделана: адрес уточняется только на сервере. Это подтверждаю как правильный подход:
сканер → исправление → повторный скан до нуля.

## 4. Замечания, не блокирующие ревью (backlog)

1. В `config.py` рекомендовано добавить `SESSION_COOKIE_SAMESITE = "Lax"` и
   `SESSION_COOKIE_SECURE` для прод-окружения (hardening).
2. Рекомендую ограничить размер тела запросов импорта (`MAX_CONTENT_LENGTH`) — защита от DoS.

Оба пункта не связаны с найденными уязвимостями и могут быть выполнены позже.

## 5. Вердикт

**Approved** (self-review). Все пункты чек-листа закрыты, повторные сканы чистые:

| Скан | Было (`main`) | Стало (`fix/security`) |
|---|---|---|
| semgrep (SAST) | 14 findings | **0** — `reports/sast-after.txt` |
| bandit (SAST) | 12 issues | **0** — `reports/bandit-after.txt` |
| pip-audit (SCA) | 33 уязвимости | **0** — `reports/sca-after.json` |
