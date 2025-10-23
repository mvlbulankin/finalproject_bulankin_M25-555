import logging
import time

from .config import ParserConfig
from .updater import RatesUpdater

logger = logging.getLogger("ValutaTrade")

class RateScheduler:
    def __init__(self, config: ParserConfig, interval_seconds: int = 3600):
        self.updater = RatesUpdater(config)
        self.interval = interval_seconds

    def start(self):
        logger.info(f"Starting scheduler with interval {self.interval} seconds")
        while True:
            try:
                self.updater.run_update()
                time.sleep(self.interval)
            except KeyboardInterrupt:
                logger.info("Scheduler stopped")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
