import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
AI_PYTHON = BASE_DIR / "ai_env" / "bin" / "python"
SCRIPT = BASE_DIR / "ai_engine" / "run_tts.py"

def generate_audio(text, lang):
    result = subprocess.check_output(
        [str(AI_PYTHON), str(SCRIPT), text, lang],
        text=True
    )
    return result.strip()
