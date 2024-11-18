import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logging_base_config(file_path: str):
    """
    Настраивает базовую конфигурацию логирования.

    :param file_path: Полный путь к файлу логов, включая имя файла.
    """
    log_directory = os.path.dirname(file_path)
    log_file = file_path

    # Создание директории для логов, если она не существует
    if log_directory and not os.path.exists(log_directory):
        os.makedirs(log_directory, exist_ok=True)
        logging.debug(f"Создана директория для логов: {log_directory}")

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,  # 5 МБ
                backupCount=2,
                encoding='utf-8'
            ),
            logging.StreamHandler()  # Вывод логов в консоль
        ]
    )

    logging.debug(f"Логирование настроено. Лог-файл: {log_file}")
