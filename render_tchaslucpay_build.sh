#!/usr/bin/env bash
set -o errexit

export DJANGO_SETTINGS_MODULE=tchaslucpay.core.settings

python -m pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput

if [ "$RUN_TCHASLUCPAY_SEED" = "true" ]; then
  python manage.py seed_tchaslucpay
fi
