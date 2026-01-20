from django.contrib import admin
from .models import RecruiterProfile, InterviewInvite

@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "country", "created_at")

@admin.register(InterviewInvite)
class InterviewInviteAdmin(admin.ModelAdmin):
    list_display = ("recruiter", "candidate_user", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("recruiter__username", "candidate_user__username", "subject")
