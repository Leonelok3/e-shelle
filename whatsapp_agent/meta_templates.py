"""Read the configured Meta account and validate campaign template selections."""
import re
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.core.cache import cache


class TemplateError(ValueError):
    pass


def _get(path, params=None):
    api = urlsplit(settings.WHATSAPP_API_URL)
    version = api.path.strip('/').split('/')[0]
    if not re.fullmatch(r'v\d+\.\d+', version):
        raise TemplateError('Version API Meta invalide dans WHATSAPP_API_URL.')
    if not settings.WHATSAPP_TOKEN:
        raise TemplateError('Token Meta absent. Configure le token sur le serveur.')
    try:
        response = requests.get(f'https://graph.facebook.com/{version}/{path}',
            headers={'Authorization': f'Bearer {settings.WHATSAPP_TOKEN}'},
            params=params, timeout=(5, 15))
        data = response.json()
    except (requests.RequestException, ValueError):
        raise TemplateError('Connexion Meta indisponible. Reessaie dans quelques instants.')
    if response.status_code != 200 or 'error' in data:
        code = data.get('error', {}).get('code', '?')
        raise TemplateError(f'Meta refuse la lecture (code {code}). Verifie le compte et les permissions whatsapp_business_management du token.')
    return data


def _pages(path, params):
    rows = []
    params = dict(params, limit=100)
    for _ in range(100):
        data = _get(path, params)
        rows.extend(data.get('data', []))
        paging = data.get('paging', {})
        after = paging.get('cursors', {}).get('after')
        if not paging.get('next'):
            return rows
        if not after or after == params.get('after'):
            break
        params['after'] = after
    raise TemplateError('Liste Meta incomplete. Impossible de valider les modeles.')


def approved_templates(refresh=False):
    waba = getattr(settings, 'WHATSAPP_WABA_ID', '').strip()
    business = getattr(settings, 'WHATSAPP_BUSINESS_ID', '').strip()
    phone = settings.WHATSAPP_PHONE_ID
    # Never cache across credentials or accounts.
    import hashlib
    key = 'wa-templates:' + hashlib.sha256(f'{waba}:{business}:{phone}:{settings.WHATSAPP_TOKEN}:{settings.WHATSAPP_API_URL}'.encode()).hexdigest()
    cached = cache.get(key)
    if cached is not None and not refresh:
        return cached
    if not phone or not str(phone).isdigit():
        raise TemplateError('WHATSAPP_PHONE_ID absent ou invalide.')
    if waba and not waba.isdigit() or business and not business.isdigit():
        raise TemplateError('Identifiant Meta invalide.')
    if not waba:
        if not business:
            raise TemplateError('Configure WHATSAPP_WABA_ID (compte WhatsApp Business), ou WHATSAPP_BUSINESS_ID pour rechercher le compte associe au numero.')
        accounts = _pages(f'{business}/owned_whatsapp_business_accounts', {'fields': 'id,name'})
        accounts += _pages(f'{business}/client_whatsapp_business_accounts', {'fields': 'id,name'})
    else:
        accounts = [{'id': waba}]
    matched = []
    for account_id in dict.fromkeys(a['id'] for a in accounts):
        numbers = _pages(f'{account_id}/phone_numbers', {'fields': 'id'})
        if any(str(n['id']) == str(phone) for n in numbers):
            matched.append(account_id)
    if len(matched) != 1:
        raise TemplateError('Aucun compte WhatsApp unique associe au WHATSAPP_PHONE_ID configure. Verifie le numero de production et son WABA ID.')
    rows = _pages(f'{matched[0]}/message_templates', {'fields': 'name,status,language,category,components'})
    result = []
    for row in rows:
        if row.get('status') != 'APPROVED':
            continue
        components = row.get('components', [])
        body = next((c.get('text', '') for c in components if c.get('type') == 'BODY'), '')
        variables = re.findall(r'\{\{([^{}]+)\}\}', body)
        numbered = all(v.isdigit() for v in variables)
        count = max([int(v) for v in variables], default=0) if numbered else 0
        unsupported = not numbered or count > 20 or set(variables) != {str(i) for i in range(1, count + 1)}
        for component in components:
            kind = component.get('type')
            if kind == 'HEADER' and (component.get('format') != 'TEXT' or '{{' in component.get('text', '')):
                unsupported = True
            if kind == 'BUTTONS' and any(b.get('type') not in ('URL', 'PHONE_NUMBER') or '{{' in b.get('url', '') for b in component.get('buttons', [])):
                unsupported = True
            if kind not in ('BODY', 'HEADER', 'FOOTER', 'BUTTONS'):
                unsupported = True
        result.append({'key': row['name'] + '|' + row['language'], 'name': row['name'],
            'language': row['language'], 'category': row.get('category', ''), 'body': body,
            'parameter_count': count, 'supported': not unsupported,
            'reason': 'Ce modele demande des parametres de media, boutons ou variables nommees non pris en charge.' if unsupported else ''})
    result.sort(key=lambda t: (t['name'], t['language']))
    cache.set(key, result, 120)
    return result


def validate_selection(key, params, refresh=False):
    template = next((t for t in approved_templates(refresh) if t['key'] == key), None)
    if not template:
        raise TemplateError('Ce modele ne figure plus dans les modeles approuves du compte configure.')
    if not template['supported']:
        raise TemplateError(template['reason'])
    if not isinstance(params, list) or not all(isinstance(p, str) and 0 < len(p) <= 1024 for p in params):
        raise TemplateError('Renseigne chaque variable avec un texte non vide (1024 caracteres maximum).')
    if len(params) != template['parameter_count']:
        raise TemplateError(f"Ce modele attend {template['parameter_count']} variable(s).")
    return template


def message_parameters(campaign, message):
    name = (message.destinataire_nom or '').strip()
    if message.user_id:
        name = message.user.first_name or name
    first = name.split()[0] if name else 'Client'
    return [p.replace('{{prenom}}', first) for p in campaign.template_meta_params]


def template_preview(campaign, message):
    text = campaign.template_meta_preview
    for i, value in enumerate(message_parameters(campaign, message), 1):
        text = text.replace('{{' + str(i) + '}}', value)
    return text
