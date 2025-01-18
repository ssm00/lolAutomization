import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime
from enum import Enum
from typing import Optional


class LogType(Enum):
    PROGRAM = "program"
    BATCH = "batch"
    TEST = "test"
    SLACK_BOT = "slack_bot"

class LogManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.loggers = {}

    def get_daily_dir(self):
        today = datetime.now().strftime('%Y-%m-%d')
        daily_dir = os.path.join(self.base_dir, today)
        os.makedirs(daily_dir, exist_ok=True)
        return daily_dir

    def _create_log_file_path(self, log_type):
        daily_dir = self.get_daily_dir()
        return os.path.join(daily_dir, f"{log_type.value}.log")

    def get_logger(self, name, log_type, level = logging.INFO):
        logger_key = f"{name}_{log_type.value}"
        if logger_key in self.loggers:
            return self.loggers[logger_key]
        logger = logging.getLogger(logger_key)
        logger.setLevel(level)

        # 기존 핸들러 제거
        if logger.handlers:
            logger.handlers.clear()
        log_file = self._create_log_file_path(log_type)
        handler = logging.FileHandler(log_file, encoding='utf-8')

        formatter = logging.Formatter(
            '[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        self.loggers[logger_key] = logger
        return logger
