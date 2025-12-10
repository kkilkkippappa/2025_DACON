from __future__ import annotations

import logging
import os
from typing import Optional


def _configure_root_logger() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


_configure_root_logger()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    prefix = "hackathon"
    if name:
        return logging.getLogger(f"{prefix}.{name}")
    return logging.getLogger(prefix)

