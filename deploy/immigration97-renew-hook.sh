#!/bin/sh
set -eu
if [ "${RENEWED_LINEAGE:-}" = /etc/letsencrypt/live/immigration97.com ]; then
    /usr/sbin/nginx -t
    /usr/bin/systemctl reload nginx
fi
