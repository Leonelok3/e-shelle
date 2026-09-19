"""Canada AI regression tests: in-memory database and no production storage."""
from ai_engine.test_content_settings import *

ROOT_URLCONF = 'preparation_tests.test_urls'

# Isolate application templates from the unrelated global navigation/apps.
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'OPTIONS': {
        'loaders': [
            ('django.template.loaders.locmem.Loader', {
                'base.html': '{% block content %}{% endblock %}{% block extra_js %}{% endblock %}',
            }),
            'django.template.loaders.app_directories.Loader',
        ],
        'context_processors': ['django.template.context_processors.request',
                               'django.contrib.auth.context_processors.auth'],
    },
}]
