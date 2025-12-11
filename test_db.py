import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        row = cursor.fetchone()
        print("✅ PostgreSQL connecté :", row[0])
except Exception as e:
    print("❌ Erreur :", e)
    import traceback
    traceback.print_exc()