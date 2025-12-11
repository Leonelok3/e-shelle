from django.db import models
from django.conf import settings
from django.utils import timezone

# Import conditionnel pour ArrayField (compatible SQLite + PostgreSQL)
if 'postgresql' in settings.DATABASES['default']['ENGINE']:
    from django.contrib.postgres.fields import ArrayField
else:
    # Fallback ArrayField pour SQLite
    import json
    
    class ArrayField(models.TextField):
        """
        Simulation d'ArrayField pour SQLite en utilisant JSON.
        Compatible avec PostgreSQL pour migration future.
        """
        def __init__(self, base_field, **kwargs):
            self.base_field = base_field
            super().__init__(**kwargs)
        
        def deconstruct(self):
            name, path, args, kwargs = super().deconstruct()
            kwargs['base_field'] = self.base_field
            return name, path, args, kwargs
        
        def from_db_value(self, value, expression, connection):
            if value is None:
                return []
            if isinstance(value, list):
                return value
            return json.loads(value)
        
        def to_python(self, value):
            if isinstance(value, list):
                return value
            if value is None:
                return []
            if isinstance(value, str):
                return json.loads(value)
            return value
        
        def get_prep_value(self, value):
            if value is None:
                return '[]'
            if isinstance(value, str):
                return value
            return json.dumps(value)
        
        def value_to_string(self, obj):
            value = self.value_from_object(obj)
            return self.get_prep_value(value)


class Program(models.Model):
    code = models.SlugField(unique=True, max_length=64)
    title = models.CharField(max_length=255)
    country = models.CharField(max_length=64)
    category = models.CharField(
        max_length=16, 
        choices=[("study", "study"), ("work", "work"), ("pr", "pr")]
    )
    url_official = models.URLField()
    min_score = models.FloatField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} ({self.country})"


class ProgramCriterion(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="criteria")
    key = models.CharField(max_length=64)  # e.g., "age", "language.ielts.overall", "budget.usd"
    op = models.CharField(
        max_length=8, 
        choices=[("gte", "gte"), ("lte", "lte"), ("eq", "eq"), ("in", "in"), ("bool", "bool")]
    )
    value_json = models.JSONField()  # right-hand value(s)
    weight = models.FloatField(default=1.0)
    required = models.BooleanField(default=False)


class Session(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    locale = models.CharField(max_length=8, default="fr")
    status = models.CharField(max_length=16, default="draft")
    score_total = models.FloatField(null=True, blank=True)
    result_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class Answer(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="answers")
    key = models.CharField(max_length=64)
    value_json = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)


class ChecklistTemplate(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="checklist_templates")
    label = models.CharField(max_length=255)
    doc_code = models.CharField(max_length=64)
    is_required = models.BooleanField(default=True)


class JourneyStepTemplate(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="journey_steps")
    label = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=1)
    eta_days = models.PositiveIntegerField(default=7)

    class Meta:
        ordering = ["order"]