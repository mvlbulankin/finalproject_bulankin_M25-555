import hashlib
import logging
import secrets
from datetime import datetime
from typing import Tuple

from ..decorators import log_action
from ..infra.database import DatabaseManager
from ..infra.settings import SettingsLoader
from ..parser_service.config import ParserConfig
from ..parser_service.updater import RatesUpdater
from .exceptions import ApiRequestError
from .models import Portfolio, User
from .utils import validate_currency_code

config = ParserConfig()

settings = SettingsLoader()
db = DatabaseManager()
db.set_data_path(settings.get("data_path", "data"))
logger = logging.getLogger("ValutaTrade")

def get_pair_rate(pair: str, pairs: dict) -> float:
    """Получение курса для пары (всегда float)."""
    if pair not in pairs:
        raise ValueError(f"Курс {pair} недоступен.")
    rate_str = pairs[pair]["rate"]
    return float(rate_str)

def get_rate(from_cur: str, to_cur: str = "USD") -> Tuple[float, str]:
    """Получение курса с проверкой TTL и обновлением кэша."""
    from_cur = validate_currency_code(from_cur)
    to_cur = validate_currency_code(to_cur)
    if from_cur == to_cur:
        return 1.0, datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    rates_data = db.load("rates.json")
    if not rates_data or "pairs" not in rates_data:
        raise ValueError(
            "Курсы не загружены. Выполните update-rates чтобы загрузить данные."
        )

    pairs = rates_data["pairs"]
    ttl = settings.get("rates_ttl_seconds", 300)

    def needs_update(updated_at: str) -> bool:
        update_time = datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%S")
        return (datetime.now() - update_time).total_seconds() > ttl

    base = "USD"
    pair_from = f"{from_cur}_{base}"
    pair_to = f"{to_cur}_{base}"
    update_needed = False
    if pair_from in pairs and needs_update(pairs[pair_from]["updated_at"]):
        update_needed = True
    if pair_to in pairs and needs_update(pairs[pair_to]["updated_at"]):
        update_needed = True

    if update_needed:
        try:
            updater = RatesUpdater(config)
            updater.run_update()
            rates_data = db.load("rates.json")
            pairs = rates_data["pairs"]
        except Exception as e:
            raise ApiRequestError(f"Не удалось обновить курсы: {str(e)}")

    if to_cur == base:
        pair = pair_from
        p = pairs[pair]
        updated_at = p["updated_at"]
        rate = get_pair_rate(pair, pairs)
    elif from_cur == base:
        pair = pair_to
        p = pairs[pair]
        updated_at = p["updated_at"]
        rate_to_usd = get_pair_rate(pair, pairs)
        rate = 1 / rate_to_usd if rate_to_usd else 0
    else:
        p_from = pairs[pair_from]
        p_to = pairs[pair_to]
        updated_at = max(p_from["updated_at"], p_to["updated_at"])
        rate_from_usd = get_pair_rate(pair_from, pairs)
        rate_to_usd = get_pair_rate(pair_to, pairs)
        rate = rate_from_usd / rate_to_usd if rate_to_usd else 0

    return rate, updated_at

@log_action("REGISTER")
def register(username: str, password: str) -> int:
    """Регистрация пользователя."""
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")
    users = db.load("users.json")
    if any(u["username"] == username for u in users):
        raise ValueError(f"Имя пользователя '{username}' уже занято")
    salt = secrets.token_hex(8)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    user_id = max([u.get("user_id", 0) for u in users]) + 1 if users else 1
    reg_date = datetime.now()
    user_dict = {
        "user_id": user_id,
        "username": username,
        "hashed_password": hashed,
        "salt": salt,
        "registration_date": reg_date.strftime("%Y-%m-%dT%H:%M:%S")
    }
    db.save("users.json", users + [user_dict])
    portfolios = db.load("portfolios.json")
    portfolio_dict = {"user_id": user_id, "wallets": {}}
    db.save("portfolios.json", portfolios + [portfolio_dict])
    return user_id

@log_action("LOGIN")
def login(username: str, password: str) -> int:
    """Авторизация пользователя."""
    users = db.load("users.json")
    user = next((u for u in users if u["username"] == username), None)
    if not user:
        raise ValueError(f"Пользователь '{username}' не найден")
    salt = user["salt"]
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    if hashed != user["hashed_password"]:
        raise ValueError("Неверный пароль")
    return user["user_id"]

def show_portfolio(user_id: int, base: str = "USD") -> str:
    """Отображение портфеля с базовой валютой."""
    try:
        user_data = db.find_by_id("users.json", "user_id", user_id)
        if not user_data:
            raise ValueError("Пользователь не найден")
        username = user_data["username"]
        user = User.from_dict(user_data)
        port_data = db.find_by_id("portfolios.json", "user_id", user_id)
        if not port_data or not port_data.get("wallets"):
            return f"Портфель пользователя '{username}' пуст."
        portfolio = Portfolio.from_dict(port_data, user)
        if not portfolio.wallets:
            return f"Портфель пользователя '{username}' пуст."
        output = f"Портфель пользователя '{username}' (база: {base}):\n"
        total = portfolio.get_total_value(base)
        for code, wallet in portfolio.wallets.items():
            if code == base:
                value = wallet.balance
            else:
                try:
                    rate, _ = get_rate(code, base)
                    value = wallet.balance * rate
                except ValueError:
                    value = 0.0
            output += f"- {wallet.get_balance_info()}  → {value:.2f} {base}\n"
        output += "---------------------------------\n"
        output += f"ИТОГО: {total:.2f} {base}"
        return output
    except ValueError as e:
        return f"Ошибка загрузки портфеля: {e}. Проверьте данные."
    except Exception as e:
        return f"Портфель пользователя недоступен: {e}. Обратитесь к администратору."

@log_action("BUY")
def buy(
    user_id: int,
    currency: str,
    amount: float,
    verbose: bool = False,
) -> str:
    """Покупка валюты (упрощённо: начисление с оценкой стоимости)."""
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    currency = validate_currency_code(currency)
    user_data = db.find_by_id("users.json", "user_id", user_id)
    user = User.from_dict(user_data)
    port_data = db.find_by_id("portfolios.json", "user_id", user_id)
    portfolio = Portfolio.from_dict(port_data, user)
    try:
        usd_per_unit, _ = get_rate(currency, "USD")
    except ValueError:
        raise ValueError(
            f"Не удалось получить курс для {currency}→USD. "
            "Выполните update-rates чтобы загрузить данные."
        )

    wallet = portfolio.get_wallet(currency)
    if not wallet:
        portfolio.add_currency(currency)
        wallet = portfolio.get_wallet(currency)
    old_balance = wallet.balance
    wallet.deposit(amount)
    new_port_dict = portfolio.to_dict()
    db.update_by_id("portfolios.json", "user_id", user_id, new_port_dict)
    
    estimated_cost = amount * usd_per_unit
    output = (
        f"Покупка выполнена: {amount:.4f} {currency} "
        f"по курсу {usd_per_unit:.2f} USD/{currency}\n"
    )
    if verbose:
        output += (
            f"Изменения в портфеле:\n- {currency}: "
            f"было {old_balance:.4f} → стало {wallet.balance:.4f}"
        )
    output += f"\nОценочная стоимость покупки: {estimated_cost:.2f} USD"
    return output

@log_action("SELL")
def sell(
    user_id: int,
    currency: str,
    amount: float,
    verbose: bool = False,
) -> str:
    """Продажа валюты (упрощённо: списание с оценкой выручки)."""
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    currency = validate_currency_code(currency)
    user_data = db.find_by_id("users.json", "user_id", user_id)
    user = User.from_dict(user_data)
    port_data = db.find_by_id("portfolios.json", "user_id", user_id)
    portfolio = Portfolio.from_dict(port_data, user)
    wallet = portfolio.get_wallet(currency)
    if not wallet:
        raise ValueError(
            f"У вас нет кошелька '{currency}'. "
            "Добавьте валюту: она создаётся автоматически при первой покупке."
        )
    old_balance = wallet.balance
    wallet.withdraw(amount)
    new_port_dict = portfolio.to_dict()
    db.update_by_id("portfolios.json", "user_id", user_id, new_port_dict)
    
    if currency == "USD":
        output = f"Продажа выполнена: {amount:.4f} {currency}\n"
        if verbose:
            output += (
                f"Изменения в портфеле:\n- {currency}: "
                f"было {old_balance:.4f} → стало {wallet.balance:.4f}"
            )
        return output
    
    try:
        usd_per_unit, _ = get_rate(currency, "USD")
    except ValueError:
        raise ValueError(f"Не удалось получить курс для {currency}→USD")
    
    estimated_revenue = amount * usd_per_unit
    output = (
        f"Продажа выполнена: {amount:.4f} {currency} "
        f"по курсу {usd_per_unit:.2f} USD/{currency}\n"
    )
    if verbose:
        output += (
            f"Изменения в портфеле:\n- {currency}: "
            f"было {old_balance:.4f} → стало {wallet.balance:.4f}"
        )
    output += f"\nОценочная выручка: {estimated_revenue:.2f} USD"
    return output
