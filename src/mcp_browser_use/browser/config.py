# -*- coding: utf-8 -*-

import os
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BrowserPersistenceConfig:
    """
    Configuration for browser persistence and debugging connection settings.

    :param persistent_session: If True, reuse browser data across sessions.
    :param user_data_dir: Path to Chrome's user data directory if persistent_session is True.
    :param debugging_port: Port for remote debugging (default 9222).
    :param debugging_host: Host for remote debugging (default 'localhost').
    """

    persistent_session: bool = False
    user_data_dir: Optional[str] = None
    debugging_port: Optional[int] = None
    debugging_host: Optional[str] = None

    @classmethod
    def from_env(cls) -> "BrowserPersistenceConfig":
        """
        Create a BrowserPersistenceConfig from environment variables:
        - CHROME_PERSISTENT_SESSION=true/false
        - CHROME_USER_DATA=path/to/data
        - CHROME_DEBUGGING_PORT=9222
        - CHROME_DEBUGGING_HOST=localhost
        """
        persistent_session_str = os.getenv("CHROME_PERSISTENT_SESSION", "").lower()
        persistent_session = persistent_session_str == "true"

        user_data_dir = os.getenv("CHROME_USER_DATA")

        port_str = os.getenv("CHROME_DEBUGGING_PORT", "9222")
        try:
            debugging_port = int(port_str)
        except ValueError:
            logger.warning(
                f"Invalid CHROME_DEBUGGING_PORT='{port_str}', using default 9222."
            )
            debugging_port = 9222

        debugging_host = os.getenv("CHROME_DEBUGGING_HOST", "localhost")

        return cls(
            persistent_session=persistent_session,
            user_data_dir=user_data_dir,
            debugging_port=debugging_port,
            debugging_host=debugging_host,
        )
