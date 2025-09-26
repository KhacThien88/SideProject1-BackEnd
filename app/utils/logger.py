import logging
from typing import Optional


_configured = False


def _configure_logger() -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    _configure_logger()
    return logging.getLogger(name if name else __name__)


