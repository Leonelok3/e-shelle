# cv_generator/urls.py
from django.urls import path
from . import views

app_name = 'cv_generator'

urlpatterns = [
    # Pages générales
    path('', views.index, name='index'),
    path('cv-list/', views.cv_list, name='cv_list'),
    path('templates/', views.template_selection, name='template_selection'),
    
    # Création de CV - Étapes
    path('cv/<int:cv_id>/', views.create_cv, name='create_cv'),  # Étape 1
    path('cv/<int:cv_id>/step2/', views.create_cv_step2, name='create_cv_step2'),  # Étape 2
    path('cv/<int:cv_id>/step3/', views.create_cv_step3, name='create_cv_step3'),  # Étape 3
    
    # Expériences (SUPPRESSION UNIQUEMENT)
    path('cv/<int:cv_id>/experience/<int:exp_id>/delete/', views.delete_experience, name='delete_experience'),
    
    # Formation
    path('cv/<int:cv_id>/education/add/', views.add_education, name='add_education'),
    path('cv/<int:cv_id>/education/<int:edu_id>/delete/', views.delete_education, name='delete_education'),
    
    # Compétences
    path('cv/<int:cv_id>/skill/add/', views.add_skill, name='add_skill'),
    path('cv/<int:cv_id>/skill/<int:skill_id>/delete/', views.delete_skill, name='delete_skill'),
    
    # Langues
    path('cv/<int:cv_id>/language/add/', views.add_language, name='add_language'),
    path('cv/<int:cv_id>/language/<int:lang_id>/delete/', views.delete_language, name='delete_language'),
    
    # Certifications
    path('cv/<int:cv_id>/certification/add/', views.add_certification, name='add_certification'),
    path('cv/<int:cv_id>/certification/<int:cert_id>/delete/', views.delete_certification, name='delete_certification'),
    
    # Bénévolat
    path('cv/<int:cv_id>/volunteer/add/', views.add_volunteer, name='add_volunteer'),
    path('cv/<int:cv_id>/volunteer/<int:vol_id>/delete/', views.delete_volunteer, name='delete_volunteer'),
    
    # Projets
    path('cv/<int:cv_id>/project/add/', views.add_project, name='add_project'),
    path('cv/<int:cv_id>/project/<int:proj_id>/delete/', views.delete_project, name='delete_project'),
    
    # Loisirs
    path('cv/<int:cv_id>/hobby/add/', views.add_hobby, name='add_hobby'),
    path('cv/<int:cv_id>/hobby/<int:hobby_id>/delete/', views.delete_hobby, name='delete_hobby'),
    
    # Résumé
    path('cv/<int:cv_id>/summary/update/', views.update_summary, name='update_summary'),
    
    # Finalisation & Export
    path('cv/<int:cv_id>/complete/', views.complete_cv, name='complete_cv'),
    path('cv/<int:cv_id>/export-pdf/', views.export_pdf, name='export_pdf'),
    
    # API IA
    path('api/set-template/', views.set_template, name='set_template'),
    path('api/recommend-templates/', views.recommend_templates, name='recommend_templates'),
    path('api/generate-summary/<int:cv_id>/', views.generate_summary, name='generate_summary'),
    path('api/clarify-experience/', views.clarify_experience, name='clarify_experience'),
    path('api/enhance-experience/', views.enhance_experience, name='enhance_experience'),
    path('api/optimize-skills/', views.optimize_skills, name='optimize_skills'),
    path('api/analyze-cv/', views.analyze_cv, name='analyze_cv'),
    path('api/analyze-cv/<int:cv_id>/', views.analyze_cv, name='analyze_cv_with_id'),
]