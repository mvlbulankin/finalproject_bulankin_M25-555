import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .config import ParserConfig
from .storage import Storage

logger = logging.getLogger("ValutaTrade.Parser")

class RatesUpdater:
    def __init__(self, config: ParserConfig):
        self.cg_client = CoinGeckoClient(config)
        self.er_client = ExchangeRateApiClient(config)
        self.storage = Storage(config)
        self.clients = {"CoinGecko": self.cg_client, "ExchangeRate-API": self.er_client}

    def run_update(self, sources: Optional[List[str]] = None) -> int:
        logger.info("Starting rates update...")
        all_rates: Dict[str, Dict[str, Any]] = {}
        all_records: List[Dict[str, Any]] = []
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        source_filters = [s.lower() for s in (sources or [])]

        for source_name, client in self.clients.items():
            cleaned_source_name = source_name.lower().replace("-", "").replace(" ", "")
            if source_filters and cleaned_source_name not in source_filters:
                continue
            try:
                client_rates = client.fetch_rates()
                logger.info(
                    f"Fetching from {source_name}... OK ({len(client_rates)} rates)"
                )
                for pair, data in client_rates.items():
                    from_cur, to_cur = pair.split("_")
                    record = {
                        "id": f"{from_cur}_{to_cur}_{timestamp}",
                        "from_currency": from_cur,
                        "to_currency": to_cur,
                        "rate": data["rate"],
                        "timestamp": timestamp,
                        "source": source_name,
                        "meta": data["meta"]
                    }
                    all_records.append(record)
                    all_rates[pair] = {
                        "rate": data["rate"],
                        "updated_at": timestamp,
                        "source": source_name
                    }
            except Exception:
                logger.error(f"Failed to fetch from {source_name}: Network error.")
                continue

        if all_rates:
            self.storage.append_history(all_records)
            self.storage.save_rates(all_rates)
            logger.info(f"Writing {len(all_rates)} rates to data/rates.json...")

        total = len(all_rates)
        return total
