import json
import shlex
from datetime import datetime

from prettytable import PrettyTable

from ..core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from ..core.usecases import (
    buy,
    get_rate,
    login,
    register,
    sell,
    show_portfolio,
)
from ..core.utils import load_json
from ..infra.settings import SettingsLoader
from ..parser_service.config import ParserConfig
from ..parser_service.updater import RatesUpdater

settings = SettingsLoader()
config = ParserConfig()
current_user_id = None


def parse_args(parts: list) -> dict:
    """Парсинг аргументов команд."""
    args = {}
    i = 0
    while i < len(parts):
        if parts[i].startswith("--"):
            key = parts[i][2:]
            if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                args[key] = parts[i + 1]
                i += 2
            else:
                args[key] = True
                i += 1
        else:
            i += 1
    return args


def run_cli():
    """Основной цикл CLI."""
    global current_user_id
    print(
        "Добро пожаловать в ValutaTrade Hub. "
        "Команды: register, login, show-portfolio, "
        "buy, sell, get-rate, update-rates, show-rates, exit."
    )
    supported = settings.get("supported_currencies", [])
    while True:
        try:
            cmd = input("> ").strip()
            if not cmd:
                continue
            parts = shlex.split(cmd)
            if not parts:
                continue
            command = parts[0].lower()
            args_dict = parse_args(parts[1:])
            if command == "exit" or command == "quit":
                print("Выход из системы.")
                break
            elif command == "register":
                username = args_dict.get("username")
                password = args_dict.get("password")
                if not username or not password:
                    print("Usage: register --username <str> --password <str>")
                    continue
                try:
                    user_id = register(username, password)
                    print(
                        f"Пользователь '{username}' зарегистрирован (id={user_id}). "
                        f"Войдите: login --username {username} --password ****"
                    )
                except ValueError as e:
                    print(str(e))
            elif command == "login":
                username = args_dict.get("username")
                password = args_dict.get("password")
                if not username or not password:
                    print("Usage: login --username <str> --password <str>")
                    continue
                try:
                    user_id = login(username, password)
                    current_user_id = user_id
                    users_data = load_json("users.json")
                    username_real = next(
                        u["username"] for u in users_data if u["user_id"] == user_id
                    )
                    print(f"Вы вошли как '{username_real}'")
                except ValueError as e:
                    print(str(e))
            elif command == "show-portfolio":
                if current_user_id is None:
                    print("Сначала выполните login")
                    continue
                base = args_dict.get("base", "USD").upper()
                if base not in supported:
                    print(f"Неизвестная базовая валюта '{base}'")
                    continue
                try:
                    output = show_portfolio(current_user_id, base)
                    print(output)
                except ValueError as e:
                    print(str(e))
            elif command == "buy":
                if current_user_id is None:
                    print("Сначала выполните login")
                    continue
                currency_arg = args_dict.get("currency")
                amount_str = args_dict.get("amount")
                if not currency_arg or not amount_str:
                    print("Usage: buy --currency <str> --amount <float>")
                    continue
                try:
                    amount = float(amount_str)
                except ValueError:
                    print("'amount' должен быть положительным числом")
                    continue
                try:
                    output = buy(current_user_id, currency_arg, amount, verbose=True)
                    print(output)
                except InsufficientFundsError as e:
                    print(str(e))
                except CurrencyNotFoundError as e:
                    print(f"{str(e)}. Поддерживаемые: {', '.join(supported)}")
                except ValueError as e:
                    print(str(e))
            elif command == "sell":
                if current_user_id is None:
                    print("Сначала выполните login")
                    continue
                currency_arg = args_dict.get("currency")
                amount_str = args_dict.get("amount")
                if not currency_arg or not amount_str:
                    print("Usage: sell --currency <str> --amount <float>")
                    continue
                try:
                    amount = float(amount_str)
                except ValueError:
                    print("'amount' должен быть положительным числом")
                    continue
                try:
                    output = sell(current_user_id, currency_arg, amount, verbose=True)
                    print(output)
                except InsufficientFundsError as e:
                    print(str(e))
                except CurrencyNotFoundError as e:
                    print(f"{str(e)}. Поддерживаемые: {', '.join(supported)}")
                except ValueError as e:
                    print(str(e))
            elif command == "get-rate":
                from_arg = args_dict.get("from", "USD")
                to_arg = args_dict.get("to")
                if not to_arg:
                    print("Usage: get-rate --from <str> --to <str>")
                    continue
                try:
                    rate, updated_at = get_rate(from_arg, to_arg)
                    rev_rate = 1 / rate if rate != 0 else 0
                    print(
                        f"Курс {from_arg}→{to_arg}: {rate:.8f} "
                        f"(обновлено: {updated_at})"
                    )
                    print(f"Обратный курс {to_arg}→{from_arg}: {rev_rate:.8f}")
                except CurrencyNotFoundError as e:
                    print(f"{str(e)}. Поддерживаемые: {', '.join(supported)}.")
                except ApiRequestError as e:
                    print(
                        f"Курс {from_arg}→{to_arg} недоступен. "
                        f"Повторите попытку позже. ({str(e)})"
                    )
                except ValueError as e:
                    print(str(e))
            elif command == "update-rates":
                source = args_dict.get("source")
                sources = [source] if source else None
                try:
                    updater = RatesUpdater(config)
                    count = updater.run_update(sources)
                    last_refresh = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    if count > 0:
                        print(
                            f"Update successful. Total rates updated: "
                            f"{count}. Last refresh: {last_refresh}"
                        )
                    else:
                        print(
                            "Update completed with errors. "
                            "Check logs/parser.log for details."
                        )
                except Exception as e:
                    print(
                        f"Update failed. Error: {e}. "
                        "Check logs/parser.log for details."
                    )
            elif command == "show-rates":
                currency = args_dict.get("currency")
                top_str = args_dict.get("top")
                base = args_dict.get("base", "USD").upper()
                if base not in supported:
                    print(f"Неизвестная базовая валюта '{base}'")
                    continue
                try:
                    rates_data = load_json("rates.json")
                    if (
                        isinstance(rates_data, list)
                        or not rates_data
                        or "pairs" not in rates_data
                        or not rates_data["pairs"]
                    ):
                        raise FileNotFoundError("Кеш пуст")
                    pairs = rates_data["pairs"]
                    last_update = rates_data.get("last_refresh", "unknown")
                    print(f"Rates from cache (updated at {last_update}):")
                    table = PrettyTable(["Pair", "Rate"])
                    base_usd_pair = f"{base}_USD"
                    base_usd_rate = pairs.get(
                        base_usd_pair, {}
                    ).get("rate", 1.0) if base != "USD" else 1.0

                    if currency:
                        cur_pair = f"{currency.upper()}_{base}"
                        cur_usd_pair = f"{currency.upper()}_USD"
                        cur_usd_rate = pairs.get(cur_usd_pair, {}).get("rate", 0)
                        cur_base_rate = (
                            cur_usd_rate / base_usd_rate
                            if base != "USD" else cur_usd_rate
                        )
                        if cur_usd_rate == 0:
                            print(f"Курс для '{currency}' не найден в кеше.")
                        else:
                            table.add_row([cur_pair, f"{cur_base_rate:.5f}"])
                            print(table)
                        continue

                    if top_str:
                        top_n = int(top_str)
                        crypto_usd = {
                            k: v for k, v in pairs.items()
                            if k.split("_")[0] in config.CRYPTO_CURRENCIES
                        }
                        sorted_crypto = sorted(
                            crypto_usd.items(),
                            key=lambda x: x[1]["rate"] / base_usd_rate,
                            reverse=True,
                        )[:top_n]
                        for pair_usd, p in sorted_crypto:
                            code = pair_usd.split("_")[0]
                            rate_base = (
                                p["rate"] / base_usd_rate
                                if base != "USD" else p["rate"]
                            )
                            table.add_row([f"{code}_{base}", f"{rate_base:.2f}"])
                        print(table)
                        continue

                    for pair_usd, p in sorted(pairs.items()):
                        code = pair_usd.split("_")[0]
                        rate_usd = p["rate"]
                        rate_base = (
                            rate_usd / base_usd_rate
                            if base != "USD" else rate_usd
                        )
                        pair_base = f"{code}_{base}"
                        table.add_row([pair_base, f"{rate_base:.5f}"])
                    print(table)

                except FileNotFoundError:
                    print(
                        "Локальный кеш курсов пуст. "
                        "Выполните 'update-rates' чтобы загрузить данные."
                    )
                except json.JSONDecodeError:
                    print("Ошибка чтения кеша курсов. Выполните 'update-rates'.")
                except ValueError as e:
                    print(str(e))
            else:
                print(
                    f"Неизвестная команда '{command}'. "
                    "Используйте: register, login, show-portfolio, "
                    "buy, sell, get-rate, update-rates, show-rates, exit."
                )
        except KeyboardInterrupt:
            print("\nВыход из системы.")
            break
        except Exception as e:
            print(f"Ошибка: {e}")
