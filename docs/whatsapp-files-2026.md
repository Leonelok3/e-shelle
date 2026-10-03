# Fichiers dans la messagerie WhatsApp

La boîte de réception propose un bouton de pièce jointe, le nom et la taille du fichier sélectionné, une légende facultative et un téléchargement dans l'historique. Un échec conserve le brouillon et la sélection. Les messages entrants sont actualisés toutes les quatre secondes quand la page est visible.

Formats envoyés : PDF, TXT, Word, Excel, PowerPoint, JPG, PNG, MP3, M4A, AAC, AMR, OGG Opus, MP4 et 3GP. Limites par défaut : documents 25 Mo, images 5 Mo, audio et vidéo 16 Mo. Les codecs restent soumis à l'acceptation de Meta. WhatsApp ne permet pas de légende audio : envoyer le texte séparément.

En mode réel, un fichier peut être envoyé après un message du client datant de moins de 24 heures. Le serveur contrôle cette fenêtre avant l'envoi. Un message accepté par Meta n'est pas une preuve de livraison : les accusés du webhook mettent à jour son état. En simulation, aucun fichier n'est envoyé au contact et l'historique indique « Simulation ».

Les nouvelles pièces jointes sont conservées dans `data/whatsapp-private`, hors des fichiers publics. Leur consultation exige une session staff. Les médias entrants sont téléchargés depuis Meta lors de leur première consultation, puis conservés localement. Les anciens fichiers déjà exposés dans MEDIA_ROOT ne sont pas déplacés par cette mise à jour. Les médias distants expirés peuvent rester indisponibles : demander alors au client de les renvoyer.

## Production

Depuis la session SSH du VPS :

```bash
cd /home/eshelle/app && \
sudo -u eshelle git pull --ff-only origin main && \
sudo bash deploy/update_whatsapp.sh
```

Le script sauvegarde la base, applique la migration 0010, publie et vérifie le JavaScript, puis redémarre le service. Il suppose le stockage privé par défaut ; adapter la création du répertoire si WHATSAPP_PRIVATE_MEDIA_ROOT est personnalisé. Le diagnostic final doit indiquer un mode réel et les paramètres Meta présents pour transmettre effectivement les fichiers. Ne pas publier de jeton dans les logs.

Vérifier avec un contact de test : PDF envoyé avec légende, photo reçue, téléchargement, accès refusé sans connexion et accusé de livraison. Le webhook Meta doit être signé et configuré pour recevoir les messages. Les tests automatisés utilisent des réponses Meta simulées ; ils n'envoient aucun message réel.
