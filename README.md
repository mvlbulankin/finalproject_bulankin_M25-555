# ValutaTradeHub

Комплексная платформа для регистрации, управления портфелем фиатных/крипто валют, сделок и отслеживания курсов в реальном времени. Состоит из Core Service (CLI) и Parser Service (парсинг API).

## Установка
Склонировать репозиторий, после чего разместить .env файл в корневой директории проекта (рядом с файлом pyproject.toml). В .env файле создать переменную EXCHANGERATE_API_KEY которая содержит в себе персональный API-ключ для доступа к https://www.exchangerate-api.com/. Ключ можно получить пройдя регистрацию на сайте, это бесплатно.

```text
EXCHANGERATE_API_KEY=key_example
```

Выполнить установку проекта с помощью команды:

```bash
make install
```

### Запуск проекта

```bash
make project
```

## Команды управления

```text
Регистрация пользователя:
register --username <str> --password <str>

Авторизация пользователя:
login --username <str> --password <str>

Показать портфолио пользователя в базовой валюте (USD):
show-portfolio

Показать портфолио пользователя в кастомной валюте (например BTC):
show-portfolio --base <str>

Купить валюту:
buy --currency <str> --amount <float>

Продать валюту:
sell --currency <str> --amount <float>

Получить текущий курс:
get-rate --from <str> --to <str>

Обратиться к API и получить актуальные курсы валют:
update-rates

Показать список актуальных курсов:
show-rates

Показать N самых дорогих валют:
show-rates --top <int>

Показать курс конкретной валюты:
show-rates --currency <str>
```

## Дополнительные возможности

Реализовано логгирование на уровне INFO и ERROR в консоль, а также запись логов в файлы logs/actions.log и logs/parser.log.log

### Тестовый сценарий

```bash
register
login
show-portfolio
buy
sell
get-rate
register --username alice --password 123
register --username alice --password 1234
register --username alice --password 1234
login --username alice1234 --password 1234
login --username alice --password 123
login --username alice --password 1234
show-portfolio
buy --currency BTC --amount 250
get-rate --from ETH --to BTC
show-rates
update-rates
sell --currency ETH --amount 3
buy --currency USD --amount 30000
buy --currency ETH --amount 112
sell --currency ETH --amount 12.5
sell --currency ETH --amount 100.7
show-portfolio
sell --currency ABC --amount 1
get-rate --from ETH --to BTC
get-rate --from USD --to BTC
get-rate --from ETH --to SOL
get-rate --from ETH --to ABC
show-portfolio --base USD
show-portfolio --base ABC
show-portfolio --base BTC
show-rates
show-rates --top 2
show-rates --currency RUB
register --username professor --password 12345
login --username professor --password 12345
show-portfolio
buy --currency RUB --amount 1000
sell --currency RUB --amount 500
show-portfolio
login --username alice --password 1234
show-portfolio
```

## Запись Asciinema
[![asciicast](https://asciinema.org/a/g6QEW7vAP490ndAe5Rk3ZgdtL.svg)](https://asciinema.org/a/g6QEW7vAP490ndAe5Rk3ZgdtL)
