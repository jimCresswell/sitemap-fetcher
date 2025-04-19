"""Utility class for loading and saving processor state.

Separated from ``processor.py`` to reduce the responsibilities of
``SitemapProcessor`` and make state‑file logic easier to unit‑test in
isolation.
"""

from __future__ import annotations

import json
from typing import Dict, List


class StateManager:
    """Handles persistence and validation of processor state JSON files."""

    # Keys we expect in the persisted JSON and their expected Python types.
    REQUIRED_KEYS = {
        "sitemap_queue": list,
        "processed_sitemaps": list,
        "found_urls": list,
    }

    @classmethod
    def load_state(cls, path: str) -> Dict[str, List[str]]:
        """Load and validate a state file.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        json.JSONDecodeError
            If the file cannot be parsed as JSON.
        KeyError
            If a required key is missing.
        ValueError
            If a key has an unexpected type or the root object is not a dict.
        IOError
            For general I/O errors while reading the file.
        """
        with open(path, "r", encoding="utf-8") as fp:
            state = json.load(fp)

        if not isinstance(state, dict):
            raise ValueError("State data is not a dictionary")

        for key, expected_type in cls.REQUIRED_KEYS.items():
            if key not in state:
                raise KeyError(f"Missing required key in state: {key}")
            if not isinstance(state[key], expected_type):
                expected = expected_type.__name__
                actual = type(state[key]).__name__
                raise ValueError(
                    f"Invalid type for key '{key}': expected {expected}, got {actual}"
                )
        return state  # type: ignore[return-value]

    @staticmethod
    def save_state(path: str, state: Dict[str, List[str]]) -> None:
        """Persist *state* atomically to *path*.

        The write is done in a plain ``open(..., 'w')`` call which is
        sufficient for the symmetry with the existing implementation. If
        atomic writes are needed, a temporary file & ``os.replace`` could be
        used.
        """
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(state, fp, indent=4)
