#!/usr/bin/env bash
set -o errexit

python -m pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput

if [ "$RUN_RENDER_SEED" = "true" ]; then
  python manage.py seed_business_plans
  python manage.py seed_demo_prestataires
  python manage.py seed_facebook_marketing
  python manage.py seed_sante
  python manage.py seed_immo_demo
  python manage.py seed_auto_demo
  python manage.py seed_market_demo
  python manage.py seed_artisans_demo
  python manage.py seed_njangi_demo
fi
