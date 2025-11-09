from rest_framework import serializers
from .models import Program, ProgramCriterion, Session, Answer, ChecklistTemplate, JourneyStepTemplate

class ProgramCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgramCriterion
        fields = ("id","key","op","value_json","weight","required")

class ProgramSerializer(serializers.ModelSerializer):
    criteria = ProgramCriterionSerializer(many=True, read_only=True)
    class Meta:
        model = Program
        fields = ("id","code","title","country","category","url_official","min_score","active","criteria")

class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ("id","locale","status","score_total","result_json")

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ("id","key","value_json","created_at")
