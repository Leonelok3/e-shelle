#!/usr/bin/env bash
# Publish Artist Hub assets to the directory served by the existing E-Shelle VPS.
set -euo pipefail
cd /home/eshelle/app
source_dir="artist_hub/static/artist_hub"
target_dir="staticfiles/artist_hub"
test -f "$source_dir/css/artist_hub.css"
while IFS= read -r -d '' asset; do
    relative="${asset#"$source_dir/"}"
    destination="$target_dir/$relative"
    install -d -o eshelle -g www-data -m 755 "$(dirname "$destination")"
    install -o eshelle -g www-data -m 644 "$asset" "$destination"
done < <(find "$source_dir" -type f -print0)
echo "Fichiers Artist Hub publiés : CSS, JavaScript et affiches."
