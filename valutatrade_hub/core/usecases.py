import hashlib
import secrets
from datetime import datetime, timezone

from ..decorators import log_action
from ..infra.database import DatabaseManager
from ..infra.settings import SettingsLoader
from ..logging_config import setup_logging
from .exceptions import ApiRequestError
from .models import Portfolio, User
from .utils import validate_currency_code

# Инициализация
settings = SettingsLoader()
db = DatabaseManager()
db.set_data_path(settings.get("data_path", "data"))
logger = setup_logging(
    settings.get("log_path", "logs"),
    settings.get("log_level", "INFO"),
)


def get_pair_rate(pair: str, pairs: dict) -> float:
    """Получение курса для пары."""
    if pair not in pairs:
        raise ValueError(f"Курс {pair} недоступен.")
    return pairs[pair]["rate"]


def get_rate(from_cur: str, to_cur: str = "USD") -> float:
    """Получение курса с проверкой TTL из rates.json."""
    from_cur = validate_currency_code(from_cur)
    to_cur = validate_currency_code(to_cur)
    if from_cur == to_cur:
        return 1.0

    rates_data = db.load("rates.json")
    if not rates_data or "pairs" not in rates_data:
        raise ValueError("Курсы не загружены. Выполните update-rates.")

    pairs = rates_data["pairs"]
    ttl = settings.get("rates_ttl_seconds", 300)

    def check_ttl(updated_at: str) -> bool:
        update_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - update_time).total_seconds() > ttl:
            raise ApiRequestError("Курсы устарели. Обновите: update-rates")
        return True

    base = "USD"
    if to_cur == base:
        pair = f"{from_cur}_{base}"
        p = pairs[pair]
        check_ttl(p["updated_at"])
        return get_pair_rate(pair, pairs)
    elif from_cur == base:
        pair_to = f"{to_cur}_{base}"
        p = pairs[pair_to]
        check_ttl(p["updated_at"])
        rate_to_usd = get_pair_rate(pair_to, pairs)
        return 1 / rate_to_usd if rate_to_usd else 0
    else:
        pair_from = f"{from_cur}_{base}"
        pair_to = f"{to_cur}_{base}"
        p_from = pairs[pair_from]
        p_to = pairs[pair_to]
        check_ttl(p_from["updated_at"])
        check_ttl(p_to["updated_at"])
        rate_from_usd = get_pair_rate(pair_from, pairs)
        rate_to_usd = get_pair_rate(pair_to, pairs)
        return rate_from_usd / rate_to_usd if rate_to_usd else 0


@log_action("REGISTER") #+
def register(username: str, password: str) -> int:
    """Регистрация пользователя."""
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")
    users = db.load("users.json")
    if any(u["username"] == username for u in users):
        raise ValueError("Имя пользователя уже занято")
    salt = secrets.token_hex(8)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    user_id = max([u.get("user_id", 0) for u in users]) + 1 if users else 1
    reg_date = datetime.now()
    user_dict = {
        "user_id": user_id,
        "username": username,
        "hashed_password": hashed,
        "salt": salt,
        "registration_date": reg_date.isoformat()
    }
    db.save("users.json", users + [user_dict])
    portfolios = db.load("portfolios.json")
    portfolio_dict = {"user_id": user_id, "wallets": {}}
    db.save("portfolios.json", portfolios + [portfolio_dict])
    return user_id


@log_action("LOGIN") #+
def login(username: str, password: str) -> int:
    """Авторизация пользователя."""
    users = db.load("users.json")
    user = next((u for u in users if u["username"] == username), None)
    if not user:
        raise ValueError("Пользователь не найден")
    salt = user["salt"]
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    if hashed != user["hashed_password"]:
        raise ValueError("Неверный пароль")
    return user["user_id"]


def show_portfolio(user_id: int) -> str:#TODO необязательный аргумент --base <str>
    """Отображение портфеля."""
    user_data = db.find_by_id("users.json", "user_id", user_id)
    if not user_data:
        raise ValueError("Пользователь не найден")
    username = user_data["username"]
    user = User.from_dict(user_data)
    port_data = db.find_by_id("portfolios.json", "user_id", user_id)
    if not port_data:
        return f"Портфель пользователя '{username}' пуст."
    portfolio = Portfolio.from_dict(port_data, user)
    if not portfolio.wallets:
        return f"Портфель пользователя '{username}' пуст."
    output = f"Портфель пользователя '{username}' (база: USD):\n"
    total = portfolio.get_total_value()
    for code, wallet in portfolio.wallets.items():
        if code == "USD":
            value = wallet.balance
        else:
            rate = get_rate(code, "USD")
            value = wallet.balance * rate
        output += f"- {wallet.get_balance_info()}  → {value:.2f} USD\n"
    output += "---------------------------------\n"
    output += f"ИТОГО: {total:.2f} USD"
    return output


@log_action("BUY")#TODO нельзя покупать базовую валюту?
def buy(
    user_id: int,
    currency: str,
    amount: float,
    verbose: bool = False,
    ) -> str:
    """Покупка валюты."""
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    currency = validate_currency_code(currency)
    if currency == "USD":
        raise ValueError("Нельзя покупать базовую валюту USD")
    user_data = db.find_by_id("users.json", "user_id", user_id)
    user = User.from_dict(user_data)
    port_data = db.find_by_id("portfolios.json", "user_id", user_id)
    portfolio = Portfolio.from_dict(port_data, user)
    wallet = portfolio.get_wallet(currency)
    if not wallet:
        portfolio.add_currency(currency)
        wallet = portfolio.get_wallet(currency)
    usd_wallet = portfolio.get_wallet("USD")
    usd_per_unit = get_rate(currency, "USD")
    cost = amount * usd_per_unit
    old_usd = usd_wallet.balance
    old_balance = wallet.balance
    usd_wallet.withdraw(cost)
    wallet.deposit(amount)
    new_port_dict = portfolio.to_dict()
    db.update_by_id("portfolios.json", "user_id", user_id, new_port_dict)
    output = (
        f"Покупка выполнена: {amount:.4f} {currency} "
        f"по курсу {usd_per_unit:.2f} USD/{currency}\n"
    )
    if verbose:
        output += (
            f"Изменения в портфеле:\n- {currency}: "
            f"было {old_balance:.4f} → стало {wallet.balance:.4f}\n"
        )
        output += f"- USD: было {old_usd:.2f} → стало {usd_wallet.balance:.2f}\n"
    output += f"Оценочная стоимость покупки: {cost:.2f} USD"
    return output


@log_action("SELL")
def sell(
    user_id: int,
    currency: str,
    amount: float,
    verbose: bool = False,
    ) -> str:
    """Продажа валюты."""
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
    if currency == "USD":
        old_balance = wallet.balance
        wallet.withdraw(amount)
        new_port_dict = portfolio.to_dict()
        db.update_by_id("portfolios.json", "user_id", user_id, new_port_dict)
        output = f"Продажа выполнена: {amount:.4f} {currency}\n"
        if verbose:
            output += (
                f"Изменения в портфеле:\n- {currency}: "
                f"было {old_balance:.4f} → стало {wallet.balance:.4f}"
            )
        return output
    usd_wallet = portfolio.get_wallet("USD")
    usd_per_unit = get_rate(currency, "USD")
    revenue = amount * usd_per_unit
    old_balance = wallet.balance
    old_usd = usd_wallet.balance
    wallet.withdraw(amount)
    usd_wallet.deposit(revenue)
    new_port_dict = portfolio.to_dict()
    db.update_by_id("portfolios.json", "user_id", user_id, new_port_dict)
    output = (
        f"Продажа выполнена: {amount:.4f} {currency} "
        f"по курсу {usd_per_unit:.2f} USD/{currency}\n"
    )
    if verbose:
        output += (
            f"Изменения в портфеле:\n- {currency}: "
            f"было {old_balance:.4f} → стало {wallet.balance:.4f}\n"
        )
        output += f"- USD: было {old_usd:.2f} → стало {usd_wallet.balance:.2f}\n"
    output += f"Оценочная выручка: {revenue:.2f} USD"
    return output
