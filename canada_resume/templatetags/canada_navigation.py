"""Shared navigation registry; route names keep links and active states in sync."""
from django import template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

register = template.Library()

GROUPS = (
    ('journey', _('Mon parcours'), (
        ('immigration97:dashboard', _('Mon tableau de bord')),
        ('immigration97:assessment', _('Mon bilan de départ')),
        ('immigration97:onboarding', _('Mon objectif et mon rythme')),
    )),
    ('learn', _('Apprendre avec l’IA'), (
        ('preparation_tests:learning_center', _('Mon entraînement IA')),
        ('preparation_tests:tcf_hub', _('Préparation TCF')),
        ('preparation_tests:tef_hub', _('Préparation TEF')),
        ('preparation_tests:dashboard_global', _('Ma progression')),
        ('preparation_tests:level_mock_hub', _('Examens par niveau')),
    )),
    ('coach', _('Mon coach IA'), (
        ('preparation_tests:ai_coach', _('Coach IA de français')),
        ('canada_resume:immigration_coach', _('Coach IA immigration')),
        ('canada_resume:interview_simulation', _('Simulation d’entretien')),
    )),
    ('project', _('Mon dossier Canada'), (
        ('immigration97:dossier', _('Mes étapes de préparation')),
        ('canada_resume:dashboard', _('Mon CV et ma lettre')),
        ('canada_resume:diagnostic', _('Ma feuille de route')),
        ('canada_resume:manage_projects', _('Mon portfolio')),
        ('canada_resume:canada_resources', _('Guides et ressources')),
    )),
    ('opportunities', _('Opportunités'), (
        ('jobs:canada_jobs', _('Offres d’emploi EIMT')),
        ('jobs:canada_scholarships', _('Bourses d’études')),
        ('canada_resume:program_study', _('Guide des études')),
        ('canada_resume:program_visit', _('Préparer ma visite')),
        ('jobs:canada_visitor_opps', _('Opportunités de visite')),
        ('canada_resume:programs_hub', _('Programmes d’immigration')),
        ('canada_resume:talents_directory', _('Annuaire des talents')),
        ('jobs:canada_news', _('Actualités et tirages')),
    )),
)

# Put the most frequently requested Canada services directly in the main bar.
# The full module directory below still exposes every other route.
PRIMARY_LINKS = (
    ('preparation_tests:tcf_hub', _('TCF Canada')),
    ('jobs:canada_jobs', _('Offres d’emploi')),
    ('jobs:canada_scholarships', _('Bourses d’études')),
    ('canada_resume:program_ee', _('Entrée express')),
)


@register.simple_tag(takes_context=True)
def canada_navigation(context):
    request = context.get('request')
    match = getattr(request, 'resolver_match', None)
    name = getattr(match, 'view_name', '')
    namespace = getattr(match, 'namespace', '')
    enabled = (getattr(request, 'is_immigration97', False)
               or name == 'canada_landing' or namespace in ('canada_resume', 'immigration97')
               or namespace == 'preparation_tests'
               or name in {route for _, _, links in GROUPS for route, _ in links})
    if not enabled:
        return {'enabled': False}
    active = name
    if namespace == 'preparation_tests' and name not in {
        route for _, _, links in GROUPS for route, _ in links
    }:
        active = 'preparation_tests:tcf_hub'
    elif namespace == 'canada_resume':
        leaf = getattr(match, 'url_name', '')
        if leaf == 'program_ee':
            active = 'canada_resume:program_ee'
        elif leaf.startswith('program_') and leaf not in ('program_study', 'program_visit'):
            active = 'canada_resume:programs_hub'
        elif leaf in ('edit_profile', 'manage_experiences', 'manage_education',
                      'manage_languages', 'generate', 'generate_for_offer', 'view_resume'):
            active = 'canada_resume:dashboard'
        elif leaf == 'project_form':
            active = 'canada_resume:manage_projects'
        elif leaf == 'talent_detail':
            active = 'canada_resume:talents_directory'
    groups = []
    current = _('Accueil Canada')
    for key, label, links in GROUPS:
        items = [{'url': reverse(route), 'label': title, 'active': route == active,
                  'exact': route == name} for route, title in links]
        selected = any(item['active'] for item in items)
        if selected:
            current = next(item['label'] for item in items if item['active'])
        groups.append({'key': key, 'label': label, 'items': items,
                        'active': selected, 'url': items[0]['url']})
    primary_links = [{'url': reverse(route), 'label': label,
                      'active': route == active, 'exact': route == name}
                     for route, label in PRIMARY_LINKS]
    return {'enabled': True, 'groups': groups, 'primary_links': primary_links,
            'current': current,
            'home': name == 'canada_landing'}
