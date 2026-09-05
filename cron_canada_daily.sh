#!/bin/bash
# Script d'automatisation des tâches quotidiennes Canada pour E-Shelle

set -u
cd /home/eshelle/app || exit 1
source .venv/bin/activate || exit 1
export PYTHONUNBUFFERED=1
failed=0

echo "========================================================="
echo "DÉBUT DE LA MISE À JOUR QUOTIDIENNE CANADA : $(date)"
echo "========================================================="

echo "[1/5] Récupération des offres d'emploi EIMT/LMIA..."
python manage.py fetch_canada_jobs || failed=1

echo "[2/5] Récupération des bourses d'études..."
python manage.py fetch_canada_scholarships || failed=1

echo "[3/5] Récupération des opportunités visa visiteur..."
python manage.py fetch_canada_visitor_opps || failed=1

echo "[4/5] Récupération des actualités d'immigration..."
python manage.py fetch_canada_news || failed=1

echo "[5/5] Vérification de l'activité des liens et des expirations..."
python manage.py verify_links_and_deadlines || failed=1

echo "========================================================="
echo "FIN DE LA MISE À JOUR QUOTIDIENNE CANADA : $(date)"
echo "========================================================="

exit "$failed"
