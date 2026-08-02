import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edu_cm.settings")
django.setup()

from accounts.models import CustomUser

count = CustomUser.objects.filter(role="vendor").update(role="VENDOR")
print(f"Successfully updated {count} users to VENDOR role.")
