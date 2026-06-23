from pathlib import Path


class SubtitleGenerator:
    """Create SRT subtitles with per-scene timing."""

    def generate_srt(self, lines: list[tuple[float, float, str]], output_path: Path) -> Path:
        # lines: list of (start_seconds, end_seconds, text)
        parts = []
        for idx, (start, end, text) in enumerate(lines, start=1):
            parts.append(str(idx))
            parts.append(f"{self._format(start)} --> {self._format(end)}")
            parts.append(text)
            parts.append("")
        output_path.write_text('\n'.join(parts), encoding='utf-8')
        return output_path

    def _format(self, seconds: float) -> str:
        milliseconds = int((seconds - int(seconds)) * 1000)
        total = int(seconds)
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f'{h:02d}:{m:02d}:{s:02d},{milliseconds:03d}'
