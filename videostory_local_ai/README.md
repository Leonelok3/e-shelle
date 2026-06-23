# VideoStory Local AI

**VideoStory Local AI** est une application Django locale conçue pour Windows et VS Code. Elle transforme un prompt utilisateur en vidéo MP4 en orchestrant plusieurs briques gratuites et locales : **Ollama** pour le texte, **Stable Diffusion/ComfyUI** pour les images, **Coqui TTS ou Piper TTS** pour la voix, puis **MoviePy et FFmpeg** pour le rendu vidéo.

> Objectif fonctionnel : l’utilisateur saisit une idée, par exemple « Raconte l’histoire d’un jeune Camerounais qui obtient un visa pour le Canada », puis l’application génère le scénario, les scènes, les prompts visuels, les images, la narration audio, les sous-titres et le fichier `video_finale.mp4`.

## 1. Architecture générale

Le projet suit une architecture modulaire. Les applications Django conservent les données, tandis que le dossier `agents/` orchestre l’intelligence métier.

| Couche | Dossier | Responsabilité principale |
|---|---|---|
| Projet Django | `videostory_local_ai/` | Configuration, URLs globales, WSGI/ASGI. |
| Orchestration IA | `agents/` | Agents Story, Scene, ImagePrompt, Image, Voice, Subtitle et Video. |
| Prompt et projet | `stories/` | Modèle principal, formulaire, vues, écran de suivi. |
| Scènes | `scenes/` | Découpage narratif en scènes ordonnées. |
| Images | `images/` | Métadonnées et service Stable Diffusion/ComfyUI. |
| Voix | `voices/` | Métadonnées et service Coqui/Piper. |
| Vidéos | `videos/` | Métadonnées et assemblage MoviePy/FFmpeg. |
| Interface | `templates/`, `static/` | Pages HTML, CSS et polling JavaScript. |
| Médias générés | `media/generated/` | Images, audios, sous-titres et MP4 finaux. |

Le workflow complet est volontairement explicite afin de faciliter le débogage dans VS Code.

```text
Prompt utilisateur
    ↓
StoryAgent
    ↓
SceneAgent
    ↓
ImagePromptAgent
    ↓
ImageAgent
    ↓
VoiceAgent
    ↓
SubtitleAgent
    ↓
VideoAgent
    ↓
video_finale.mp4
```

## 2. Prérequis Windows

Installez d’abord les outils suivants sur votre machine Windows. Tous peuvent fonctionner sans API payante obligatoire.

| Outil | Rôle | Notes |
|---|---|---|
| Python 3.10 ou 3.11 | Exécution Django et MoviePy | Coqui TTS est souvent plus stable avec Python 3.10/3.11. |
| Git | Clonage et gestion du code | Recommandé avec VS Code. |
| VS Code | Développement | Installer l’extension Python. |
| FFmpeg | Encodage vidéo/audio | Ajouter `ffmpeg.exe` au `PATH`. |
| Ollama | LLM local | Télécharger un modèle comme `mistral` ou `llama3`. |
| ComfyUI ou Stable Diffusion WebUI | Génération d’images locale | ComfyUI est l’option par défaut du fichier `.env.example`. |
| Coqui TTS ou Piper | Voix off locale | Piper est souvent plus léger ; Coqui donne plus de flexibilité. |

## 3. Installation étape par étape

Créez puis ouvrez le projet dans VS Code. Dans le terminal PowerShell de VS Code, exécutez les commandes suivantes depuis le dossier du projet.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

L’application sera disponible à l’adresse `http://127.0.0.1:8000/`.

## 4. Configuration Ollama

Installez Ollama, puis téléchargez au moins un modèle local.

```powershell
ollama pull mistral
ollama pull llama3
ollama serve
```

Dans `.env`, choisissez le modèle à utiliser.

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
```

Le fichier `agents/local_llm.py` appelle l’endpoint local `/api/generate` d’Ollama. Aucun appel à une API cloud payante n’est nécessaire.

## 5. Configuration images avec ComfyUI ou Stable Diffusion WebUI

Par défaut, le projet utilise ComfyUI.

```env
IMAGE_BACKEND=comfyui
COMFYUI_BASE_URL=http://127.0.0.1:8188
```

Le service `images/services.py` contient également un backend `sdwebui` compatible avec l’API locale d’Automatic1111/Stable Diffusion WebUI.

```env
IMAGE_BACKEND=sdwebui
SD_WEBUI_BASE_URL=http://127.0.0.1:7860
```

Si aucun serveur d’image n’est disponible, le service crée une image placeholder. Ce comportement permet de tester le workflow Django, MoviePy et la base de données avant d’installer les modèles lourds.

## 6. Configuration voix avec Coqui TTS ou Piper

Le backend par défaut est Coqui TTS.

```env
VOICE_BACKEND=coqui
COQUI_TTS_MODEL=tts_models/fr/css10/vits
```

Pour Piper, configurez le chemin de l’exécutable et le modèle vocal.

```env
VOICE_BACKEND=piper
PIPER_EXE=piper
PIPER_MODEL=models/fr_FR-siwis-medium.onnx
```

Si le moteur TTS n’est pas encore installé, le service génère un fichier WAV silencieux. Cette stratégie évite de bloquer les tests d’assemblage vidéo.

## 7. Explication des fichiers principaux

### 7.1 Projet Django

| Fichier | Description |
|---|---|
| `manage.py` | Point d’entrée standard pour les commandes Django : migrations, serveur local, shell. |
| `videostory_local_ai/settings.py` | Configure SQLite, les apps Django, les chemins médias, les paramètres Ollama, ComfyUI, Stable Diffusion, Coqui, Piper et FFmpeg. |
| `videostory_local_ai/urls.py` | Expose l’administration Django et inclut les routes de l’application `stories`. |
| `videostory_local_ai/wsgi.py` | Entrée WSGI pour un serveur Python classique. |
| `videostory_local_ai/asgi.py` | Entrée ASGI si vous voulez plus tard ajouter WebSocket ou tâches temps réel. |

### 7.2 Application `stories/`

| Fichier | Description |
|---|---|
| `stories/models.py` | Définit `StoryProject`, le modèle central contenant le prompt, le scénario, le statut, la progression, l’erreur éventuelle et la vidéo finale. |
| `stories/forms.py` | Définit `StoryPromptForm`, formulaire Django utilisé sur la page d’accueil. |
| `stories/views.py` | Gère la page d’accueil, la page détail et l’endpoint JSON de progression. Le lancement du workflow se fait dans un thread local. |
| `stories/urls.py` | Déclare les routes `home`, `detail` et `status`. |
| `stories/admin.py` | Rend les projets consultables depuis l’administration Django. |

### 7.3 Application `scenes/`

| Fichier | Description |
|---|---|
| `scenes/models.py` | Définit `Scene`, chaque scène ayant un ordre, un titre, une description, une narration, un prompt image et une durée. |
| `scenes/admin.py` | Permet d’inspecter les scènes dans l’admin Django. |

### 7.4 Application `images/`

| Fichier | Description |
|---|---|
| `images/models.py` | Définit `GeneratedImage`, liée à une scène par relation one-to-one. |
| `images/services.py` | Implémente `LocalImageService`, qui appelle ComfyUI ou Stable Diffusion WebUI, puis sauvegarde une image PNG. |
| `images/admin.py` | Permet de vérifier les images générées et le backend utilisé. |

### 7.5 Application `voices/`

| Fichier | Description |
|---|---|
| `voices/models.py` | Définit `VoiceOver`, liée à une scène et contenant le fichier audio généré. |
| `voices/services.py` | Implémente `LocalVoiceService`, compatible avec Coqui TTS et Piper. |
| `voices/admin.py` | Permet d’inspecter les voix off générées. |

### 7.6 Application `videos/`

| Fichier | Description |
|---|---|
| `videos/models.py` | Définit `VideoRender`, journalisant chaque rendu MP4. |
| `videos/services.py` | Implémente `LocalVideoService`, qui assemble les images et les voix avec MoviePy, encode en H.264/AAC via FFmpeg, puis produit un MP4. |
| `videos/admin.py` | Permet de suivre les rendus vidéo. |

### 7.7 Dossier `agents/`

| Agent | Fichier | Rôle |
|---|---|---|
| BaseAgent | `agents/base.py` | Classe commune pour gérer les callbacks de progression. |
| OllamaClient | `agents/local_llm.py` | Client HTTP local vers Ollama et helper d’extraction JSON. |
| StoryAgent | `agents/story_agent.py` | Génère le scénario principal à partir du prompt utilisateur. |
| SceneAgent | `agents/scene_agent.py` | Convertit le scénario en scènes structurées. |
| ImagePromptAgent | `agents/image_prompt_agent.py` | Produit des prompts Stable Diffusion en anglais, adaptés au format 16:9. |
| ImageAgent | `agents/image_agent.py` | Appelle le service d’images local pour chaque scène. |
| VoiceAgent | `agents/voice_agent.py` | Appelle le service TTS local pour chaque narration. |
| SubtitleAgent | `agents/subtitle_agent.py` | Écrit un fichier `.srt` par scène. |
| VideoAgent | `agents/video_agent.py` | Lance l’assemblage MP4. |
| VideoStoryOrchestrator | `agents/orchestrator.py` | Exécute toute la chaîne dans le bon ordre et met à jour la progression Django. |

### 7.8 Interface utilisateur

| Fichier | Description |
|---|---|
| `templates/base.html` | Layout HTML commun : barre supérieure, chargement CSS et conteneur principal. |
| `templates/stories/home.html` | Page d’accueil avec formulaire de prompt et liste des projets récents. |
| `templates/stories/detail.html` | Page de suivi avec barre de progression, message d’étape, lecteur vidéo et détails des scènes. |
| `static/css/app.css` | Style sombre moderne, responsive, adapté à une application vidéo locale. |
| `static/js/progress.js` | Interroge périodiquement l’endpoint JSON de statut et affiche automatiquement le lecteur vidéo final. |

## 8. Utilisation

Lancez d’abord les services locaux nécessaires : Ollama, puis ComfyUI ou Stable Diffusion WebUI, puis éventuellement votre moteur TTS. Ensuite, démarrez Django.

```powershell
python manage.py runserver
```

Ouvrez `http://127.0.0.1:8000/`, saisissez un prompt et cliquez sur **Générer la vidéo**. La page de détail affiche la progression et le lecteur vidéo final dès que le rendu est terminé.

## 9. Points importants pour la production locale

Le lancement dans un thread Django est suffisant pour un prototype local dans VS Code. Pour une version plus robuste, il est recommandé d’ajouter une file de tâches locale comme Celery avec Redis local, Dramatiq ou Huey. Le projet actuel évite volontairement cette complexité afin de rester simple, gratuit et facile à exécuter sur Windows.

Les modèles Stable Diffusion et TTS peuvent être lourds. Il est conseillé de tester d’abord avec les placeholders intégrés, puis d’activer progressivement ComfyUI ou Stable Diffusion WebUI, et enfin Coqui ou Piper.

## 10. Commandes utiles

| Action | Commande |
|---|---|
| Créer les migrations | `python manage.py makemigrations` |
| Appliquer les migrations | `python manage.py migrate` |
| Créer un admin | `python manage.py createsuperuser` |
| Lancer le serveur | `python manage.py runserver` |
| Tester Ollama | `ollama run mistral` |
| Vérifier FFmpeg | `ffmpeg -version` |

## 11. Améliorations recommandées

Une prochaine itération peut ajouter une vraie file de tâches, un écran de configuration des modèles, des styles vidéo prédéfinis, la génération de sous-titres incrustés dans l’image, un système de voix par personnage, une galerie de projets, et un mode batch pour générer plusieurs vidéos à la suite.

## 12. Références

[1]: https://docs.djangoproject.com/ "Django Documentation"  
[2]: https://ollama.com/ "Ollama"  
[3]: https://github.com/comfyanonymous/ComfyUI "ComfyUI GitHub"  
[4]: https://github.com/AUTOMATIC1111/stable-diffusion-webui "Stable Diffusion WebUI GitHub"  
[5]: https://github.com/coqui-ai/TTS "Coqui TTS GitHub"  
[6]: https://github.com/rhasspy/piper "Piper TTS GitHub"  
[7]: https://zulko.github.io/moviepy/ "MoviePy Documentation"  
[8]: https://ffmpeg.org/ "FFmpeg"
