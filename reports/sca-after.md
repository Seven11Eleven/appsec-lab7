# SCA-отчёт (pip-audit) — после обновления зависимостей

- Команда: `pip-audit -r requirements.txt -f json -o reports/sca-after.json`
- Окружение: Python 3.13, pip-audit 2.10.1, база известных уязвимостей — OSV (pdpo 2026-10)
- Результат: **No known vulnerabilities found**

## Зависимости после фикса (все `vulns: []`, см. `sca-after.json`)

| Пакет | Версия |
|---|---|
| flask | 3.1.3 |
| werkzeug | 3.1.9 |
| jinja2 | 3.1.6 |
| markupsafe | 3.0.4 |
| click | 8.1.8 |
| itsdangerous | 2.2.0 |
| requests | 2.33.0 |
| urllib3 | 2.8.0 |
| pyyaml | 6.0.3 |
| gunicorn | 23.0.0 |

## Что было до фикса

33 известные уязвимости (PYSEC/CVE-аналоги) в 6 пакетах — см. `reports/sca-initial.md`.
Список закрыт обновлением пинов в `requirements.txt` (коммит `0b47f45`).

## Замечание по интерпретатору

Актуальные `urllib3` (`2.8.0`) и `requests` (`2.33.0`) требуют Python ≥ 3.10 — поэтому
SCA-скан выполняется в CI (`setup-python@3.12`) или локально на системном
`python3.11`/`python3.13`. При pyenv-3.9 разрешение этих версий невозможно (см. README).
