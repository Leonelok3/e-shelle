from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Program, ProgramCriterion, Session, Answer, ChecklistTemplate, JourneyStepTemplate

admin.site.register(Program)
admin.site.register(ProgramCriterion)
admin.site.register(Session)
admin.site.register(Answer)
admin.site.register(ChecklistTemplate)
admin.site.register(JourneyStepTemplate)
