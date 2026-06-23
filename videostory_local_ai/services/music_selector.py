from pathlib import Path
import random


class MusicSelector:
    """Select a royalty-free music file from media/music folder."""

    def __init__(self):
        self.folder = Path('media/music')
        self.folder.mkdir(parents=True, exist_ok=True)

    def pick(self) -> Path:
        files = [p for p in self.folder.iterdir() if p.suffix.lower() in ('.mp3', '.wav', '.ogg')]
        if not files:
            raise FileNotFoundError('No music files found in media/music')
        return random.choice(files)
