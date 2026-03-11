#!/bin/bash
# Script d'import des leçons allemandes en production
# À lancer sur le serveur après git pull
# Usage: bash scripts/import_german_lessons_server.sh

set -e
echo "=== Import leçons allemandes A1→C2 ==="

LEVELS="A1 A2 B1 B2 C1 C2"

for level in $LEVELS; do
    echo ""
    echo "--- Niveau $level ---"
    for batch in 1 2 3 4 5; do
        FILE="data/lessons_json/de_${level}_batch${batch}.json"
        if [ -f "$FILE" ]; then
            echo "Import: $FILE"
            python manage.py import_german_lessons --file "$FILE" --continue-on-error
        fi
    done
done

echo ""
echo "=== Vérification finale ==="
python manage.py shell -c "
from GermanPrepApp.models import GermanLesson
for level in ['A1','A2','B1','B2','C1','C2']:
    count = GermanLesson.objects.filter(exam__level=level).count()
    print(f'{level}: {count} leçons')
print('TOTAL:', GermanLesson.objects.count())
"
echo "=== Import terminé ==="
