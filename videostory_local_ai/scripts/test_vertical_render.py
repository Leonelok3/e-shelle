"""Script de test: assemble quelques images placeholders en vertical 1080x1920."""
from pathlib import Path
from PIL import Image
from moviepy.editor import AudioFileClip
from videos.services import LocalVideoService


def create_placeholder(path: Path, text: str, size=(1080, 1920), color=(18, 24, 38)):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new('RGB', size[::-1], color=color)
    img.save(path)


def create_silent_wav(path: Path, duration=3.0, sr=22050):
    import wave, struct
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(duration * sr)
    with wave.open(str(path), 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(struct.pack('<' + 'h' * frames, *([0] * frames)))


def run_test():
    base = Path('media/generated/test_vertical')
    imgs = []
    for i in range(1, 4):
        p = base / f'img_{i}.png'
        create_placeholder(p, f'Placeholder {i}')
        imgs.append(p)

    # create fake project-like object with scenes
    class SceneLike:
        def __init__(self, image_path):
            self.generated_image = type('G', (), {'image': type('I', (), {'path': str(image_path)})})
            self.voice_over = type('V', (), {'audio': str()})
            self.duration_seconds = 3.0

    class ProjectLike:
        pk = 'test'
        def __init__(self, imgs):
            self._scenes = [SceneLike(p) for p in imgs]
        def scenes(self):
            return self._scenes

    # LocalVideoService expects project.scenes.select_related(...).all()
    # We'll monkey-patch with a simple attribute used in render_project loop
    project = type('P', (), {})()
    project.pk = 'test'
    # build scenes with generated_image and voice_over objects that expose .image.path and .audio.path
    def all_scenes():
        out = []
        for p in imgs:
            gi = type('GI', (), {'image': type('IP', (), {'path': str(p)})})()
            audio_file = Path('media/generated/test_vertical') / (p.stem + '.wav')
            create_silent_wav(audio_file, duration=3.0)
            vo = type('VO', (), {'audio': type('AP', (), {'path': str(audio_file)})})()
            s = type('S', (), {'generated_image': gi, 'voice_over': vo, 'duration_seconds': 3.0})()
            out.append(s)
        return out

    project.scenes = type('Q', (), {'select_related': lambda *a, **k: type('R', (), {'all': lambda self=0: all_scenes()})()})()

    svc = LocalVideoService()
    out = svc.render_project(project, resolution=(1080, 1920), ken_burns=True)
    print('Rendered to', out)


if __name__ == '__main__':
    run_test()
