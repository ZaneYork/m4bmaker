import logging
from pathlib import Path


def logger_factory(
    name: str = __name__,
    log_path: Path = Path.cwd() / "m4bmaker.log",
    console_level: int = logging.WARNING,
    file_level: int = logging.DEBUG,
) -> logging.Logger:
    """Factory method to create a logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:  # Avoid adding duplicate handlers
        return logger

    formatter = logging.Formatter(
        fmt="{asctime} | {name} | {levelname:<8} | {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8", mode="w")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
