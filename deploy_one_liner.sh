#!/bin/bash
# 🚀 DÉPLOIEMENT INSTANTANÉ CE - ONE-LINER POUR VPS
# Copiez-collez cette commande complète dans votre terminal VPS

# ============================================================
# CONNEXION SSH + DÉPLOIEMENT COMPLET EN UNE SEULE COMMANDE
# ============================================================

ssh ubuntu@31.97.196.197 << 'REMOTE_EOF'

cd /home/ubuntu/e-shelle

echo "🚀 DÉPLOIEMENT CE INSTANTANÉ..."
echo ""

# Git pull
echo "[1/6] Git pull..."
git pull origin main > /dev/null 2>&1

# Permissions script
chmod +x deploy_ce_final.sh

# Exécution déploiement
echo "[2/6] Exécution script de déploiement..."
bash deploy_ce_final.sh

REMOTE_EOF

echo ""
echo "✅ Déploiement terminé!"
echo ""
echo "Vérifiez que tout fonctionne:"
echo "  🔗 https://immigration97.com"
echo "  📊 https://immigration97.com/admin"
echo ""
