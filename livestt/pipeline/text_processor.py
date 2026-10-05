"""Turns raw STT output into readable sentences and tracks the committed (finalized) vs.
in-progress (partial) text so the UI can render "committed + current partial" without ever
re-appending or duplicating a partial fragment.
"""
from __future__ import annotations

import re

_SENTENCE_END_RE = re.compile(r'[.!?…]["\')\]]?\s*$')
_WHITESPACE_RE = re.compile(r"\s+")


class TextProcessor:
    def __init__(self):
        self._committed = ""

    def reset(self) -> None:
        self._committed = ""

    @property
    def committed_text(self) -> str:
        return self._committed

    @staticmethod
    def clean(text: str) -> str:
        return _WHITESPACE_RE.sub(" ", text).strip()

    def commit_final(self, raw_text: str) -> str:
        """Finalizes an utterance: cleans it up into a proper sentence and appends it to
        the committed transcript. Returns the new committed text."""
        text = self.clean(raw_text)
        if not text:
            return self._committed

        if text[0].isalpha():
            text = text[0].upper() + text[1:]
        if not _SENTENCE_END_RE.search(text):
            text += "."

        if self._committed and not self._committed.endswith((" ", "\n")):
            self._committed += " "
        self._committed += text
        return self._committed

    def full_text(self, partial_raw: str = "") -> str:
        """Committed text plus the current in-flight partial, freshly composed each call
        (never appended), so repeated partial updates cannot duplicate content."""
        partial = self.clean(partial_raw)
        if not partial:
            return self._committed
        sep = "" if (not self._committed or self._committed.endswith(" ")) else " "
        return f"{self._committed}{sep}{partial}"
