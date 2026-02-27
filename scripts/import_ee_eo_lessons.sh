#!/bin/bash
# ============================================================
# Script d'import des leçons EE et EO générées par ChatGPT
# À exécuter sur le serveur de production depuis la racine du projet
#
# Usage :
#   chmod +x scripts/import_ee_eo_lessons.sh
#   ./scripts/import_ee_eo_lessons.sh
# ============================================================

set -e  # Arrêter si une commande échoue

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MANAGE="$BASE_DIR/manage.py"
DATA_DIR="$BASE_DIR/data/lessons_json"
PYTHON="${PYTHON:-python}"

echo "============================================================"
echo " Import des leçons EE et EO — $(date)"
echo " Répertoire : $BASE_DIR"
echo "============================================================"

run_import() {
    local file="$1"
    local label="$2"
    echo ""
    echo "--- $label ---"
    $PYTHON "$MANAGE" import_json_lessons \
        --file "$file" \
        --continue-on-error
}

# ── EE (Expression Écrite) ──────────────────────────────────
run_import "$DATA_DIR/ee_A1.json" "EE A1 (exam_id=32)"
run_import "$DATA_DIR/ee_A2.json" "EE A2 (exam_id=33)"
run_import "$DATA_DIR/ee_B1.json" "EE B1 (exam_id=34)"
run_import "$DATA_DIR/ee_B2.json" "EE B2 (exam_id=35)"
run_import "$DATA_DIR/ee_C1.json" "EE C1 (exam_id=36)"
run_import "$DATA_DIR/ee_C2.json" "EE C2 (exam_id=37)"

# ── EO (Expression Orale) ───────────────────────────────────
run_import "$DATA_DIR/eo_A1.json" "EO A1 (exam_id=26)"
run_import "$DATA_DIR/eo_A2.json" "EO A2 (exam_id=27)"
run_import "$DATA_DIR/eo_B1.json" "EO B1 (exam_id=28)"
run_import "$DATA_DIR/eo_B2.json" "EO B2 (exam_id=29)"
run_import "$DATA_DIR/eo_C1.json" "EO C1 (exam_id=30)"
run_import "$DATA_DIR/eo_C2.json" "EO C2 (exam_id=31)"

echo ""
echo "============================================================"
echo " Import terminé — $(date)"
echo "============================================================"
