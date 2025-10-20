#!/usr/bin/env python3
from valutatrade_hub.cli.interface import run_cli
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import setup_logging

settings = SettingsLoader()
setup_logging(
    settings.get("log_path", "logs"),
    settings.get("log_level", "INFO"),
)


def main():
    run_cli()


if __name__ == "__main__":
    main()
