import logging
import sys


def setup_logging() -> logging.Logger:
  """Configure application-wide logging."""
  # Create formatter
  formatter = logging.Formatter(
    fmt="%(asctime)s │ %(levelname)-7s │ %(name)-20s │ %(message)s",
    datefmt="%H:%M:%S",
  )

  # Console handler
  console_handler = logging.StreamHandler(sys.stdout)
  console_handler.setFormatter(formatter)
  console_handler.setLevel(logging.DEBUG)

  # Root logger
  root_logger = logging.getLogger()
  root_logger.setLevel(logging.INFO)
  root_logger.addHandler(console_handler)

  # Reduce noise from discord.py internals
  logging.getLogger("discord").setLevel(logging.WARNING)
  logging.getLogger("discord.http").setLevel(logging.WARNING)

  return root_logger


def get_logger(name: str) -> logging.Logger:
  """Get a logger for a specific module."""
  return logging.getLogger(name)
