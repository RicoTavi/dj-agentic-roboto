"""
Reads the optional Last.fm API key without it ever passing through source code.

Resolution order:
  1. the LASTFM_API_KEY environment variable, then
  2. the local, gitignored file  lastfm_api_key.txt  (first non-comment line).

If neither yields a key, returns None and the system runs in offline mode
against the committed cache - so a missing key is a supported state, not an error.
"""

import os
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT / "lastfm_api_key.txt"
_PLACEHOLDER = "PASTE_YOUR_KEY_HERE"


def load_lastfm_key() -> Optional[str]:
    """Returns the Last.fm API key if configured, else None."""
    env = os.environ.get("LASTFM_API_KEY", "").strip()
    if env:
        return env
    if KEY_FILE.exists():
        for line in KEY_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line != _PLACEHOLDER:
                return line
    return None


def has_lastfm_key() -> bool:
    """True when a usable Last.fm API key is configured."""
    return load_lastfm_key() is not None
