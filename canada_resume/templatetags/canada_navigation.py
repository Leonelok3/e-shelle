"""Shared navigation registry; route names keep links and active states in sync."""
from django import template
from django.urls import reverse

register = template.Library()

GROUPS = (
    ('journey', 'Mon parcours', (
        ('immigration97:dashboard', 'Mon tableau de bord'),
        ('immigration97:assessment', 'Mon bilan de départ'),
        ('immigration97:onboarding', 'Mon objectif et mon rythme'),
    )),
    ('learn', 'Apprendre avec l’IA', (
        ('preparation_tests:learning_center', 'Mon entraînement IA'),
        ('preparation_tests:tcf_hub', 'Préparation TCF'),
        ('preparation_tests:tef_hub', 'Préparation TEF'),
        ('preparation_tests:dashboard_global', 'Ma progression'),
        ('preparation_tests:level_mock_hub', 'Examens par niveau'),
    )),
    ('coach', 'Mon coach IA', (
        ('preparation_tests:ai_coach', 'Coach IA de français'),
        ('canada_resume:immigration_coach', 'Coach IA immigration'),
        ('canada_resume:interview_simulation', 'Simulation d’entretien'),
    )),
    ('project', 'Mon dossier Canada', (
        ('immigration97:dossier', 'Mes étapes de préparation'),
        ('canada_resume:dashboard', 'Mon CV et ma lettre'),
        ('canada_resume:diagnostic', 'Ma feuille de route'),
        ('canada_resume:manage_projects', 'Mon portfolio'),
        ('canada_resume:canada_resources', 'Guides et ressources'),
    )),
    ('opportunities', 'Opportunités', (
        ('jobs:canada_jobs', 'Offres d’emploi EIMT'),
        ('jobs:canada_scholarships', 'Bourses d’études'),
        ('canada_resume:program_study', 'Guide des études'),
        ('canada_resume:program_visit', 'Préparer ma visite'),
        ('jobs:canada_visitor_opps', 'Opportunités de visite'),
        ('canada_resume:programs_hub', 'Programmes d’immigration'),
        ('canada_resume:talents_directory', 'Annuaire des talents'),
        ('jobs:canada_news', 'Actualités et tirages'),
    )),
)


@register.simple_tag(takes_context=True)
def canada_navigation(context):
    request = context.get('request')
    match = getattr(request, 'resolver_match', None)
    name = getattr(match, 'view_name', '')
    namespace = getattr(match, 'namespace', '')
    enabled = (name == 'canada_landing' or namespace in ('canada_resume', 'immigration97')
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
        if leaf.startswith('program_') and leaf not in ('program_study', 'program_visit'):
            active = 'canada_resume:programs_hub'
        elif leaf in ('edit_profile', 'manage_experiences', 'manage_education',
                      'manage_languages', 'generate', 'generate_for_offer', 'view_resume'):
            active = 'canada_resume:dashboard'
        elif leaf == 'project_form':
            active = 'canada_resume:manage_projects'
        elif leaf == 'talent_detail':
            active = 'canada_resume:talents_directory'
    groups = []
    current = 'Accueil Canada'
    for key, label, links in GROUPS:
        items = [{'url': reverse(route), 'label': title, 'active': route == active,
                  'exact': route == name} for route, title in links]
        selected = any(item['active'] for item in items)
        if selected:
            current = next(item['label'] for item in items if item['active'])
        groups.append({'key': key, 'label': label, 'items': items,
                       'active': selected, 'url': items[0]['url']})
    return {'enabled': True, 'groups': groups, 'current': current,
            'home': name == 'canada_landing'}
