"""Session setup and transcript writing."""

import logging
from datetime import datetime
from pathlib import Path


def setup_session() -> tuple[Path, Path]:
    """Create a timestamped session directory under logs/ and return paths."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path("logs") / f"session_{timestamp}"
    session_dir.mkdir(parents=True, exist_ok=True)
    transcript_file = session_dir / "transcript.txt"

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return transcript_file, session_dir


class TranscriptWriter:
    """Writes output simultaneously to the console and a transcript file."""

    def __init__(self, transcript_file: Path):
        self._file = open(transcript_file, "w", encoding="utf-8")

    def write(self, text: str, end: str = "", flush: bool = True) -> None:
        print(text, end=end, flush=flush)
        self._file.write(text + end)
        if flush:
            self._file.flush()

    def write_to_file(self, text: str) -> None:
        """Write to transcript only, not to console."""
        self._file.write(text)
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
        return False
