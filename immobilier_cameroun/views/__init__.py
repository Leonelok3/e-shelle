"""
views/__init__.py — immobilier_cameroun
Package des vues immobilières.
Garantit la rétro-compatibilité totale avec views.py historique
tout en intégrant les modules de vues spécialisés (whatsapp_import).
"""
import os
import importlib.util

# Charger automatiquement toutes les vues historiques de views.py s'il existe
_legacy_views_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "views.py")
if os.path.exists(_legacy_views_path):
    spec = importlib.util.spec_from_file_location("immobilier_cameroun._views_legacy", _legacy_views_path)
    _mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_mod)
    for _name, _val in _mod.__dict__.items():
        if not _name.startswith("__"):
            globals()[_name] = _val

# Importer et exposer les vues WhatsApp
from .whatsapp_import import (
    import_whatsapp_view,
    whatsapp_drafts_view,
    valider_draft_view,
    rejeter_draft_view,
    modifier_draft_view,
    execute_draft_validation,
)
