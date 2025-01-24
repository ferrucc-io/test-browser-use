# -*- coding: utf-8 -*-


"""
If we plan to scale or have multiple agents, we might remove the singleton pattern or differentiate them by agent ID.
"""

import asyncio
from typing import Any, Optional


class AgentState:
    """
    Tracks an asynchronous stop signal and stores the last valid browser state.

    request_stop() sets an asyncio.Event, is_stop_requested() checks if it's set,
    clear_stop() resets the event and last_valid_state.
    """

    def __init__(self) -> None:
        self._stop_requested = asyncio.Event()
        self._last_valid_state: Optional[Any] = None

    def request_stop(self) -> None:
        self._stop_requested.set()

    def clear_stop(self) -> None:
        self._stop_requested.clear()
        self._last_valid_state = None

    def is_stop_requested(self) -> bool:
        return self._stop_requested.is_set()

    def set_last_valid_state(self, state: Any) -> None:
        self._last_valid_state = state

    def get_last_valid_state(self) -> Optional[Any]:
        return self._last_valid_state
