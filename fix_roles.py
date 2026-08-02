import os
import django

# Load production .env file
env_path = "/var/www/e-shelle/.env"
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edu_cm.settings")
django.setup()

from accounts.models import CustomUser

count = CustomUser.objects.filter(role="vendor").update(role="VENDOR")
print(f"Successfully updated {count} users to VENDOR role.")
