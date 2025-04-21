import logging
import sys


class LoggedException(Exception):
    """Custom exception class that logs the error message."""

    def __init__(self, message: str, logger: logging.Logger) -> None:
        super().__init__(message)
        logger.error(message, exc_info=bool(sys.exc_info()[2]))
        logger.info("Program stopped!")


class LoggedValueError(LoggedException):
    """Custom exception for value errors."""

    pass


class LoggedFileError(LoggedException):
    """Custom exception for invalid input file."""

    pass
