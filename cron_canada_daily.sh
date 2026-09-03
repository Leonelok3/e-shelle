#!/bin/bash
# Script d'automatisation des tâches quotidiennes Canada pour E-Shelle

cd /home/eshelle/app
source .venv/bin/activate

echo "========================================================="
echo "DÉBUT DE LA MISE À JOUR QUOTIDIENNE CANADA : $(date)"
echo "========================================================="

echo "[1/5] Récupération des offres d'emploi EIMT/LMIA..."
python manage.py fetch_canada_jobs

echo "[2/5] Récupération des bourses d'études..."
python manage.py fetch_canada_scholarships

echo "[3/5] Récupération des opportunités visa visiteur..."
python manage.py fetch_canada_visitor_opps

echo "[4/5] Récupération des actualités d'immigration..."
python manage.py fetch_canada_news

echo "[5/5] Vérification de l'activité des liens et des expirations..."
python manage.py verify_links_and_deadlines

echo "========================================================="
echo "FIN DE LA MISE À JOUR QUOTIDIENNE CANADA : $(date)"
echo "========================================================="
