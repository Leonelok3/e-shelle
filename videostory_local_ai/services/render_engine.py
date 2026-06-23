from pathlib import Path
from typing import Tuple
from moviepy.editor import VideoFileClip


class RenderEngine:
    """Low-level render utilities and encoder selection for FFmpeg."""

    def transcode(self, input_path: Path, output_path: Path, codec: str = 'libx264', audio_codec: str = 'aac') -> Path:
        clip = VideoFileClip(str(input_path))
        clip.write_videofile(str(output_path), codec=codec, audio_codec=audio_codec)
        clip.close()
        return output_path
