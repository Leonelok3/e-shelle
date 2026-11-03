# TCF quotidien : progression, oral et surveillance

## Suivi du compte

Pour un compte connecte, la derniere tentative quotidienne est enregistree par date et peut etre reprise depuis un autre appareil. Le hub presente les quatre competences, les resultats disponibles et les seances recentes. Les visiteurs non connectes conservent leur tentative dans leur session de navigateur. Les resultats sont des retours pedagogiques, pas des scores officiels.

La migration `0032_tcfdailyprogress` ajoute une table isolee de progression. Elle ne modifie pas les resultats historiques ni les autres parcours.

## Expression orale

La rotation EO couvre les trois types de tache :

- Tache 1 : entretien dirige, 2 minutes.
- Tache 2 : interaction simulee, 2 minutes de preparation puis 3 minutes 30 d'echange.
- Tache 3 : point de vue sans preparation, 4 minutes 30.

L'eleve s'entraine seul a partir d'un scenario ; aucun examinateur en direct n'est simule. L'envoi volontaire d'un enregistrement declenche transcription et correction avec les fournisseurs IA existants. Le fichier audio est temporaire et supprime apres traitement. La transcription et le retour sont conserves dans la seance. L'IA ne note pas les criteres acoustiques.

## Niveau et longueur

Le niveau transmis au correcteur suit la progression TCF mesuree lorsqu'elle comporte deja des tentatives, puis le niveau du profil. En l'absence de niveau, A1 sert de valeur de depart. Une production EE hors limite reste corrigeable, mais l'interface explique que la note de respect du format est moins representative.

## Controle de qualite et sante

Executer `python manage.py check_tcf_daily` apres generation des audios et periodiquement. La commande verifie les documents, les preuves des QCM, la rotation des taches EO et les sept fichiers audio. Le script de deploiement installe un timer systemd horaire ; consulter son dernier resultat avec `systemctl status eshelle-tcf-daily-health.service` et ses journaux avec `journalctl -u eshelle-tcf-daily-health.service`. Les erreurs de transcription et de correction sont consignees dans les journaux Django sans y inclure les productions de l'eleve.

```bash
python manage.py prepare_tcf_daily_audio
python manage.py check_tcf_daily
```

## Publication

Le script cible `deploy/update_tcf_daily.sh` sauvegarde la base, applique la migration additive, prepare/verifie les audios, publie les actifs statiques et active le controle horaire. Il ne lance pas la reparation des contenus TCF/TEF existants. Sur le VPS, apres livraison du commit et avec le depot propre :

```bash
sudo bash deploy/update_tcf_daily.sh
```

Le script verifie les pages et compare les actifs statiques servis aux fichiers de la release. La sauvegarde est conservee sous `/home/eshelle/backups/tcf-daily/`.
