"""Private attachments and Meta Cloud API media operations."""
import mimetypes
import codecs
import re
import uuid
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from PIL import Image

MB = 1024 * 1024
FORMATS = {
    '.pdf': ('document', 'application/pdf', 100),
    '.txt': ('document', 'text/plain', 100),
    '.doc': ('document', 'application/msword', 100),
    '.docx': ('document', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 100),
    '.xls': ('document', 'application/vnd.ms-excel', 100),
    '.xlsx': ('document', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 100),
    '.ppt': ('document', 'application/vnd.ms-powerpoint', 100),
    '.pptx': ('document', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 100),
    '.jpg': ('image', 'image/jpeg', 5), '.jpeg': ('image', 'image/jpeg', 5),
    '.png': ('image', 'image/png', 5),
    '.mp4': ('video', 'video/mp4', 16), '.3gp': ('video', 'video/3gpp', 16),
    '.mp3': ('audio', 'audio/mpeg', 16), '.m4a': ('audio', 'audio/mp4', 16),
    '.aac': ('audio', 'audio/aac', 16), '.amr': ('audio', 'audio/amr', 16),
    '.ogg': ('audio', 'audio/ogg', 16),
}


def private_storage():
    root = getattr(settings, 'WHATSAPP_PRIVATE_MEDIA_ROOT', settings.BASE_DIR / 'data' / 'whatsapp-private')
    return FileSystemStorage(location=root)


def clean_filename(name):
    name = str(name or 'fichier').replace('\\', '/').split('/')[-1]
    name = re.sub(r'[\x00-\x1f\x7f"<>]', '_', name)
    return name[:255] or 'fichier'


def validate_upload(upload):
    filename = clean_filename(upload.name)
    extension = Path(filename).suffix.lower()
    if extension not in FORMATS:
        raise ValidationError('Format non pris en charge. Choisissez un PDF, document Office, TXT, JPG, PNG, audio ou vidéo compatible.')
    kind, mime, provider_limit = FORMATS[extension]
    limit = min(int(getattr(settings, 'WHATSAPP_ATTACHMENT_MAX_MB', 25)), provider_limit) * MB
    if not upload.size or upload.size > limit:
        raise ValidationError(f'Fichier vide ou trop volumineux : maximum {limit // MB} Mo pour ce format.')
    prefix = upload.read(4096)
    upload.seek(0)
    valid = True
    try:
        if kind == 'image':
            with Image.open(upload) as image:
                valid = image.format == ('PNG' if extension == '.png' else 'JPEG')
                image.verify()
        elif extension == '.pdf':
            valid = prefix.startswith(b'%PDF-')
        elif extension in ('.doc', '.xls', '.ppt'):
            valid = prefix.startswith(bytes.fromhex('d0cf11e0a1b11e1'))
        elif extension in ('.docx', '.xlsx', '.pptx'):
            part = {'.docx': 'word/document.xml', '.xlsx': 'xl/workbook.xml', '.pptx': 'ppt/presentation.xml'}[extension]
            with zipfile.ZipFile(upload) as archive:
                valid = '[Content_Types].xml' in archive.namelist() and part in archive.namelist()
        elif extension == '.txt':
            valid = b'\x00' not in prefix
            codecs.getincrementaldecoder('utf-8-sig')().decode(prefix, final=upload.size <= len(prefix))
        elif extension in ('.mp4', '.3gp', '.m4a'):
            valid = prefix[4:8] == b'ftyp'
        elif extension == '.ogg':
            valid = prefix.startswith(b'OggS') and b'OpusHead' in prefix
        elif extension == '.amr':
            valid = prefix.startswith(b'#!AMR')
        elif extension == '.mp3':
            valid = prefix.startswith(b'ID3') or len(prefix) > 1 and prefix[0] == 255 and prefix[1] & 224 == 224
        elif extension == '.aac':
            valid = len(prefix) > 1 and prefix[0] == 255 and prefix[1] & 246 == 240
    except (OSError, ValueError, zipfile.BadZipFile, UnicodeError, Image.DecompressionBombError):
        valid = False
    finally:
        upload.seek(0)
    if not valid:
        raise ValidationError('Le contenu du fichier ne correspond pas à son format, ou le fichier est endommagé.')
    return {'filename': filename, 'kind': kind, 'mime': mime, 'size': upload.size}


def save_private(upload, filename):
    name = f'{timezone.now():%Y/%m}/{uuid.uuid4().hex}/{clean_filename(filename)}'
    return 'private:' + private_storage().save(name, upload)


def api_base():
    # Reuse the configured Graph version, rather than a hard-coded old version.
    url = getattr(settings, 'WHATSAPP_API_URL', '').rstrip('/')
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'graph.facebook.com':
        raise ValueError('Configuration de l’API Meta invalide.')
    parts = parsed.path.strip('/').split('/')
    if len(parts) < 3 or parts[-1] != 'messages':
        raise ValueError('URL des messages Meta invalide.')
    return f'https://graph.facebook.com/{parts[0]}'


def send_attachment(number, upload, metadata, caption=''):
    if getattr(settings, 'WHATSAPP_DRY_RUN', True):
        return {'success': True, 'message_id': f'dryrun-file-{uuid.uuid4().hex}',
                'media_id': '', 'simulation': True, 'erreur': 'Simulation : aucun fichier envoyé à WhatsApp.'}
    token = getattr(settings, 'WHATSAPP_TOKEN', '')
    phone = getattr(settings, 'WHATSAPP_PHONE_ID', '')
    if not token or not phone:
        return {'success': False, 'erreur': 'Configuration Meta incomplète.'}
    try:
        upload.seek(0)
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.post(f'{api_base()}/{phone}/media', headers=headers,
            data={'messaging_product': 'whatsapp', 'type': metadata['mime']},
            files={'file': (metadata['filename'], upload, metadata['mime'])}, timeout=(10, 60))
        data = response.json()
        if response.status_code not in (200, 201) or not data.get('id'):
            return {'success': False, 'erreur': meta_error(data, 'Impossible de transférer le fichier à WhatsApp.')}
        media_id = data['id']
        media = {'id': media_id}
        if metadata['kind'] == 'document':
            media['filename'] = metadata['filename']
        if caption and metadata['kind'] != 'audio':
            media['caption'] = caption
        payload = {'messaging_product': 'whatsapp', 'to': re.sub(r'\D', '', number),
                   'type': metadata['kind'], metadata['kind']: media}
        response = requests.post(settings.WHATSAPP_API_URL, headers=headers, json=payload, timeout=(10, 30))
        data = response.json()
        if response.status_code in (200, 201) and data.get('messages'):
            return {'success': True, 'message_id': data['messages'][0]['id'], 'media_id': media_id, 'erreur': ''}
        return {'success': False, 'media_id': media_id, 'erreur': meta_error(data, 'WhatsApp a refusé le fichier.')}
    except (requests.RequestException, ValueError, KeyError):
        return {'success': False, 'erreur': 'La confirmation Meta n’a pas pu être obtenue. Vérifiez l’historique avant de réessayer.'}


def meta_error(data, fallback):
    error = data.get('error', {}) if isinstance(data, dict) else {}
    code = error.get('code', '')
    if code == 131047:
        return 'La fenêtre WhatsApp de 24 heures est fermée. Attendez un nouveau message du client avant d’envoyer un fichier.'
    return f"{fallback} {error.get('message', '')} (code {code})".strip()


def download_attachment(media_id, media_type='', filename='', mime_type=''):
    if not media_id or getattr(settings, 'WHATSAPP_DRY_RUN', True):
        return ''
    token = getattr(settings, 'WHATSAPP_TOKEN', '')
    if not token:
        return ''
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'{api_base()}/{media_id}', headers=headers, timeout=(10, 15))
        if response.status_code != 200:
            return ''
        data = response.json()
        url = data.get('url', '')
        host = urlparse(url).hostname or ''
        if urlparse(url).scheme != 'https' or not (host == 'facebook.com' or host.endswith('.facebook.com')
                or host == 'fbcdn.net' or host.endswith('.fbcdn.net')
                or host == 'fbsbx.com' or host.endswith('.fbsbx.com')):
            return ''
        if int(data.get('file_size') or 0) > 100 * MB:
            return ''
        mime = data.get('mime_type') or mime_type
        extension = mimetypes.guess_extension(mime or '') or {'image': '.jpg', 'document': '.pdf', 'audio': '.ogg', 'video': '.mp4', 'sticker': '.webp'}.get(media_type, '.bin')
        name = clean_filename(filename or f'{media_type or "fichier"}{extension}')
        from tempfile import SpooledTemporaryFile
        from django.core.files import File
        with requests.get(url, headers=headers, timeout=(10, 60), stream=True, allow_redirects=False) as remote:
            if remote.status_code != 200:
                return ''
            with SpooledTemporaryFile(max_size=2 * MB) as buffer:
                size = 0
                for chunk in remote.iter_content(64 * 1024):
                    size += len(chunk)
                    if size > 100 * MB:
                        return ''
                    buffer.write(chunk)
                if not size:
                    return ''
                buffer.seek(0)
                return save_private(File(buffer, name=name), name)
    except (requests.RequestException, ValueError, OSError):
        return ''
