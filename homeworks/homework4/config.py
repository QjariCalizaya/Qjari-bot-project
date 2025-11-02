import os
from dataclasses import dataclass
import logging

import dotenv


@dataclass
class Config:
    token: str
    openrouter_api_key: str
    db_path: str
    log_file: str
    log_level: str


def setup_logger(filepath: str, level: str = 'INFO') -> logging.Logger:
    numeric_level = getattr(logging, level.upper(), None)

    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')

    logger = logging.getLogger('telegram-bot')
    logger.setLevel(numeric_level)
    logger.propagate = False # Disable forwarding to the root logger

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(filepath, mode='a', encoding='utf-8')
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_config() -> Config:
    dotenv_path = dotenv.find_dotenv()

    if dotenv_path:
        dotenv.load_dotenv(dotenv_path, override=False)
    else:
        raise FileNotFoundError('Could not find .env file')

    return Config(
        token=os.getenv('TOKEN'),
        openrouter_api_key=os.getenv('OPENROUTER_API_KEY'),
        db_path=os.getenv('DB_PATH'),
        log_file=os.getenv('LOG_FILE') or './bot.log',
        log_level=os.getenv('LOG_LEVEL') or 'INFO',
    )


config = get_config()
logger = setup_logger(config.log_file, config.log_level)