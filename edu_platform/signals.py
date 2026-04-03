"""
Signaux Django pour edu_platform.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger('edu_platform')
