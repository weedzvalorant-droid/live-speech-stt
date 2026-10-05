"""Saves the transcript to TXT/Markdown. Clipboard copy is a one-line Qt call left to the
UI layer (QClipboard is a GUI-thread concern); this module only builds the text content.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


class ExportManager:
    @staticmethod
    def to_txt(text: str, path: str | Path) -> None:
        Path(path).write_text(text, encoding="utf-8")

    @staticmethod
    def to_markdown(text: str, path: str | Path, title: str = "Live Speech Transcript") -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()] or [text]
        body = "\n\n".join(paragraphs)
        content = f"# {title}\n\n_{timestamp}_\n\n{body}\n"
        Path(path).write_text(content, encoding="utf-8")
